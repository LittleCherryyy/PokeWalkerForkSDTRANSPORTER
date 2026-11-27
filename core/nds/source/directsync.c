/* Automatic DSi -> Android handoff over the hotspot gateway. GPL-3.0-or-later.
 * The Android app listens on TCP/30821; the DSi is always the client. */
#include "syncnet.h"
#include "lease.h"
#include "walkerfile.h"
#include "walker_directsync.h"
#include "walker_push_stream.h"
#include <stdio.h>
#include <string.h>

static char legacyEndpoint[64];

#ifdef __NDS__
#include "wifi_setup.h"
#include <dswifi9.h>
#include <3ds.h>
#include <errno.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <time.h>

enum DirectState {
  DIRECT_OFF,
  DIRECT_WAIT_WIFI,
  DIRECT_CONNECTING,
  DIRECT_WAIT_PHONE,
  DIRECT_SEND_ARM_HEADER,
  DIRECT_READ_ARM_ACK,
  DIRECT_SEND_HEADER,
  DIRECT_SEND_WALKER,
  DIRECT_READ_HEADER,
  DIRECT_READ_ERROR,
  DIRECT_RETURNING,
  DIRECT_DONE,
  DIRECT_FAILED
};

static int directMode, directState, directSocket = -1;
static int directReturnMode;
static char selected[600], endpoint[48], statusText[160];
static char sessionText[WALKER_DIRECT_SESSION_SIZE + 1];
static char trainerKey[WALKER_DIRECT_TRAINER_SIZE + 1];
static unsigned char pendingToken[16];
static int pendingCheckout, returnConfirmOnly, transferAuthorized;
static unsigned char payload[WALKER_DIRECT_WALKER_SIZE];
static unsigned char requestHeader[WALKER_DIRECT_HEADER_SIZE];
static unsigned char responseHeader[WALKER_DIRECT_HEADER_SIZE];
static unsigned char errorBody[160];
static unsigned char returnStage[WALKER_DIRECT_WALKER_SIZE];
static WalkerPushStream returnStream;
static uint32_t returnCrcState, returnPayloadCrc;
static unsigned sentHeader, sentPayload, receivedHeader, receivedError;
static uint32_t payloadCRC;
static uint64_t deadline;
static struct in_addr hotspotGateway;
static SyncBeforeCheckout beforeCheckout;
static SyncEvent onEvent;
static unsigned tokenCounter;
static unsigned lastReturnProgress;

#define DIRECT_CHUNK 1024u
#define DIRECT_CONNECT_TIMEOUT_MS 15000u
#define DIRECT_PHONE_RETRY_MS 2000u
#define DIRECT_IO_TIMEOUT_MS 60000u

static uint64_t directNow(void) { return osGetTime(); }

static int readWalkerFile(const char *path, unsigned char *out) {
  FILE *f = fopen(path, "rb");
  if (!f) return 0;
  int ok = fread(out, 1, WALKER_DIRECT_WALKER_SIZE, f) ==
           WALKER_DIRECT_WALKER_SIZE;
  if (ok) ok = fgetc(f) == EOF && !ferror(f);
  if (fclose(f)) ok = 0;
  return ok;
}

static void buildRequestHeader(unsigned op, unsigned flags, unsigned length,
                               uint32_t crc) {
  memset(requestHeader, 0, sizeof(requestHeader));
  memcpy(requestHeader, WALKER_DIRECT_MAGIC, WALKER_DIRECT_MAGIC_SIZE);
  requestHeader[8] = WALKER_DIRECT_VERSION;
  requestHeader[9] = (unsigned char)op;
  walkerDirectPut16(requestHeader + 10, flags);
  walkerDirectPut32(requestHeader + 12, length);
  walkerDirectPut32(requestHeader + 16, crc);
  memcpy(requestHeader + 20, sessionText, WALKER_DIRECT_SESSION_SIZE);
  memcpy(requestHeader + 52, trainerKey, WALKER_DIRECT_TRAINER_SIZE);
}

static int prepareWalker(void) {
  WalkerLease lease;
  int locked = leaseInspect(selected, &lease);
  WalkerInfo info;
  pendingCheckout = 0;
  returnConfirmOnly = 0;
  transferAuthorized = 0;
  if (locked < 0) {
    snprintf(statusText, sizeof(statusText),
             "Walker lock is damaged. Keep its recovery files.");
    return 0;
  }
  if (locked) {
    char phonePath[620];
    if (lease.revoked) {
      snprintf(statusText, sizeof(statusText),
               "This session was revoked. Use walker recovery.");
      return 0;
    }
    if (snprintf(phonePath, sizeof(phonePath), "%s.phone", selected) >=
            (int)sizeof(phonePath) ||
        !readWalkerFile(phonePath, payload) ||
        walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE) != lease.baseCrc) {
      snprintf(statusText, sizeof(statusText),
               "Saved handoff copy failed verification. Nothing was sent.");
      return 0;
    }
    leaseTokenText(lease.token, sessionText);
  } else {
    if (beforeCheckout && !beforeCheckout()) {
      snprintf(statusText, sizeof(statusText),
               "Console save failed. Resolve it before sending.");
      return 0;
    }
    if (!readWalkerFile(selected, payload) ||
        !walkerRead(payload, &info) || !walkerCanWalk(payload) ||
        !info.hasPokemon || !walkerTrainerKey(payload, trainerKey)) {
      snprintf(statusText, sizeof(statusText),
               "A valid walker with a Pokémon is required for DSi Sync.");
      return 0;
    }
    uint64_t ticks = directNow();
    uint32_t seed = walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE) ^
                    (uint32_t)ticks ^ (uint32_t)(ticks >> 32) ^
                    (uint32_t)time(0) ^ hotspotGateway.s_addr ^ ++tokenCounter;
    if (!seed) seed = 0x6d2b79f5u;
    for (unsigned i = 0; i < sizeof(pendingToken); i++) {
      seed ^= seed << 13;
      seed ^= seed >> 17;
      seed ^= seed << 5;
      pendingToken[i] = (unsigned char)(seed >> ((i & 3u) * 8));
    }
    leaseTokenText(pendingToken, sessionText);
    pendingCheckout = 1;
  }
  if (!walkerRead(payload, &info) || !walkerCanWalk(payload) ||
      !info.hasPokemon || !walkerTrainerKey(payload, trainerKey)) {
    snprintf(statusText, sizeof(statusText),
             "Saved walker has no transferable Pokémon. Recovery copy kept.");
    return 0;
  }
  payloadCRC = walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE);
  buildRequestHeader(WALKER_DIRECT_ARM_PUSH, 0, 0, payloadCRC);
  sentHeader = sentPayload = receivedHeader = receivedError = 0;
  snprintf(statusText, sizeof(statusText),
           "Connected to hotspot. Waiting for Connect to Console approval on TCP 30821.");
  return 1;
}

static int prepareDirectReturn(void) {
  WalkerLease lease;
  WalkerInfo info;
  int locked = leaseInspect(selected, &lease);
  if (locked != 1 || !lease.direct || lease.revoked) {
    snprintf(statusText, sizeof(statusText),
             "No active direct phone session is available to return.");
    return 0;
  }
  leaseTokenText(lease.token, sessionText);
  char phonePath[620];
  if (snprintf(phonePath, sizeof(phonePath), "%s.phone", selected) >=
          (int)sizeof(phonePath) ||
      !readWalkerFile(phonePath, payload) ||
      walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE) != lease.baseCrc ||
      !walkerRead(payload, &info) || !walkerCanWalk(payload) ||
      !info.hasPokemon || !walkerTrainerKey(payload, trainerKey)) {
    snprintf(statusText, sizeof(statusText),
             "Phone recovery copy failed verification. Nothing was changed.");
    return 0;
  }
  char error[160] = {0};
  pendingCheckout = 0;
  transferAuthorized = 0;
  int pending = leaseDirectReturnPending(selected, lease.token, payload,
                                         error, sizeof(error));
  if (pending < 0) {
    snprintf(statusText, sizeof(statusText), "%.150s", error);
    return 0;
  }
  returnConfirmOnly = pending == 1;
  transferAuthorized = 0;
  buildRequestHeader(WALKER_DIRECT_ARM_PULL, returnConfirmOnly ? 1u : 0u,
                     0, 0);
  sentHeader = 0;
  receivedHeader = 0;
  receivedError = 0;
  snprintf(statusText, sizeof(statusText),
           "Verified phone session. Waiting for Connect to Console approval.");
  return 1;
}

static void closeSocket(int force) {
  if (directSocket < 0) return;
  if (force) forceclosesocket(directSocket);
  else closesocket(directSocket);
  directSocket = -1;
}

static void failDirect(const char *message) {
  closeSocket(1);
  snprintf(statusText, sizeof(statusText), "%s", message);
  directState = DIRECT_FAILED;
}

static void beginAuthorizedTransfer(void) {
  if (directReturnMode) {
    memset(&returnStream, 0, sizeof(returnStream));
    if (returnConfirmOnly) {
      returnPayloadCrc = walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE);
      returnStream.phase = WALKER_PUSH_FAILED;
      if (walkerConfirmBegin(&returnStream, sessionText, returnPayloadCrc)) {
        failDirect("Could not resume the staged phone return.");
        return;
      }
      snprintf(statusText, sizeof(statusText),
               "App approved. Confirming the saved return receipt.");
    } else {
      returnPayloadCrc = 0;
      returnCrcState = 0;
      lastReturnProgress = 0;
      if (walkerPullBegin(&returnStream, payload, returnStage, sessionText,
                          trainerKey)) {
        failDirect("Could not start the phone return request.");
        return;
      }
      snprintf(statusText, sizeof(statusText),
               "App approved. Receiving the Pokémon from the phone.");
    }
    transferAuthorized = 1;
    directState = DIRECT_RETURNING;
    deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    return;
  }

  if (pendingCheckout) {
    WalkerLease lease;
    char error[160] = {0};
    if (!leaseCheckout(selected, pendingToken, payload, 1, &lease, error,
                       sizeof(error))) {
      if (leaseInspect(selected, 0) == 1 && onEvent) onEvent(1);
      snprintf(statusText, sizeof(statusText), "Checkout stopped: %.120s",
               error);
      directState = DIRECT_FAILED;
      closeSocket(1);
      return;
    }
    pendingCheckout = 0;
    if (onEvent) onEvent(1);
    leaseTokenText(lease.token, sessionText);
    char committedTrainer[WALKER_DIRECT_TRAINER_SIZE + 1];
    WalkerInfo info;
    if (!walkerRead(payload, &info) || !walkerCanWalk(payload) ||
        !info.hasPokemon || !walkerTrainerKey(payload, committedTrainer) ||
        strcmp(committedTrainer, trainerKey) ||
        walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE) != payloadCRC) {
      failDirect("Approved walker changed before checkout. The SD recovery copy is kept.");
      return;
    }
  }
  payloadCRC = walkerCrc(payload, WALKER_DIRECT_WALKER_SIZE);
  buildRequestHeader(WALKER_DIRECT_PUSH_TO_PHONE, 0,
                     WALKER_DIRECT_WALKER_SIZE, payloadCRC);
  sentHeader = sentPayload = receivedHeader = receivedError = 0;
  transferAuthorized = 1;
  directState = DIRECT_SEND_HEADER;
  deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
  snprintf(statusText, sizeof(statusText),
           "App approved. Sending the verified Pokewalker snapshot.");
}

static void waitForPhone(void) {
  closeSocket(1);
  directState = DIRECT_WAIT_PHONE;
  deadline = directNow() + DIRECT_PHONE_RETRY_MS;
  snprintf(statusText, sizeof(statusText),
           "Waiting for Connect to Console on TCP 30821. Retrying.");
}

static int nonblocking(int s) {
  int one = 1;
  return ioctl(s, FIONBIO, &one) == 0;
}

static int returnSocketWrite(void *context, const unsigned char *data,
                             unsigned count) {
  (void)context;
  int n = send(directSocket, data, count, 0);
  if (n > 0) { deadline = directNow() + DIRECT_IO_TIMEOUT_MS; return n; }
  if (!n) return 0;
  if (errno == EWOULDBLOCK || errno == EAGAIN || errno == EINTR) return 0;
  return -1;
}
static int returnSocketRead(void *context, unsigned char *data,
                            unsigned count) {
  (void)context;
  int n = recv(directSocket, data, count, 0);
  if (n > 0) { deadline = directNow() + DIRECT_IO_TIMEOUT_MS; return n; }
  if (!n) return -1;
  if (errno == EWOULDBLOCK || errno == EAGAIN || errno == EINTR) return 0;
  return -1;
}
static const WalkerPushIo returnIo = {returnSocketWrite, returnSocketRead};

static void phoneAccepted(void) {
  sentHeader = receivedHeader = receivedError = 0;
  directState = DIRECT_SEND_ARM_HEADER;
  deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
  snprintf(statusText, sizeof(statusText),
           "Phone accepted TCP. Waiting for Connect to Console approval.");
}

static void beginConnect(void) {
  struct sockaddr_in remote;
  memset(&remote, 0, sizeof(remote));
  remote.sin_family = AF_INET;
  remote.sin_addr = hotspotGateway;
  remote.sin_port = htons(WALKER_DIRECT_PORT);
  directSocket = socket(AF_INET, SOCK_STREAM, 0);
  if (directSocket < 0) {
    failDirect("DSi could not create a TCP socket.");
    return;
  }
  if (!nonblocking(directSocket)) {
    failDirect("DSi could not set the TCP socket nonblocking.");
    return;
  }
  snprintf(statusText, sizeof(statusText),
           "Waiting for Connect to Console on TCP 30821.");
  int rc = connect(directSocket, (struct sockaddr *)&remote, sizeof(remote));
  if (!rc) {
    phoneAccepted();
  } else if (errno == EINPROGRESS || errno == EWOULDBLOCK || errno == EAGAIN) {
    directState = DIRECT_CONNECTING;
    deadline = directNow() + DIRECT_CONNECT_TIMEOUT_MS;
  } else {
    waitForPhone();
  }
}

static void buildErrorStatus(void) {
  unsigned n = receivedError;
  if (n >= sizeof(errorBody)) n = sizeof(errorBody) - 1;
  errorBody[n] = 0;
  if (!n) {
    snprintf(statusText, sizeof(statusText),
             "Phone rejected the transfer. Check its DSi Sync status.");
  } else {
    for (unsigned i = 0; i < n; i++)
      if (errorBody[i] < 32 || errorBody[i] > 126) errorBody[i] = ' ';
    snprintf(statusText, sizeof(statusText), "Phone rejected: %.130s",
             (const char *)errorBody);
  }
  closeSocket(0);
  directState = DIRECT_FAILED;
}

static void validateArmResponseHeader(void) {
  if (memcmp(responseHeader, WALKER_DIRECT_MAGIC, WALKER_DIRECT_MAGIC_SIZE) ||
      responseHeader[8] != WALKER_DIRECT_VERSION ||
      responseHeader[10] != 0 || responseHeader[11] != 0 ||
      memcmp(responseHeader + 20, sessionText, WALKER_DIRECT_SESSION_SIZE) ||
      memcmp(responseHeader + 52, trainerKey, WALKER_DIRECT_TRAINER_SIZE)) {
    failDirect("Phone returned an invalid Connect to Console response.");
    return;
  }
  unsigned length = walkerDirectBe32(responseHeader + 12);
  if (responseHeader[9] == WALKER_DIRECT_ERROR) {
    if (length > sizeof(errorBody)) {
      failDirect("Phone error response was too large.");
      return;
    }
    receivedError = 0;
    if (!length) buildErrorStatus();
    else {
      directState = DIRECT_READ_ERROR;
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    }
    return;
  }
  if (responseHeader[9] != WALKER_DIRECT_READY || length != 0 ||
      walkerDirectBe32(responseHeader + 16) != 0) {
    failDirect("The app has not armed this transfer direction. Open Connect to Console first.");
    return;
  }
  snprintf(statusText, sizeof(statusText),
           "Connect to Console approved. Preparing the Pokémon transfer.");
  beginAuthorizedTransfer();
}

static void validateResponseHeader(void) {
  if (memcmp(responseHeader, WALKER_DIRECT_MAGIC, WALKER_DIRECT_MAGIC_SIZE) ||
      responseHeader[8] != WALKER_DIRECT_VERSION ||
      memcmp(responseHeader + 20, sessionText, WALKER_DIRECT_SESSION_SIZE)) {
    failDirect("Phone returned an invalid DSi Sync frame.");
    return;
  }
  unsigned length = walkerDirectBe32(responseHeader + 12);
  if (responseHeader[9] == WALKER_DIRECT_ERROR) {
    if (length > sizeof(errorBody)) {
      failDirect("Phone error response was too large.");
      return;
    }
    receivedError = 0;
    if (!length) buildErrorStatus();
    else {
      directState = DIRECT_READ_ERROR;
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    }
    return;
  }
  if (responseHeader[9] != WALKER_DIRECT_OK || length != 0 ||
      walkerDirectBe32(responseHeader + 16) != 0 ||
      memcmp(responseHeader + 52, trainerKey, WALKER_DIRECT_TRAINER_SIZE)) {
    failDirect("Phone acknowledgement did not match this walker.");
    return;
  }
  closeSocket(0);
  snprintf(statusText, sizeof(statusText),
           "Pokémon received and saved by the Android app.");
  directState = DIRECT_DONE;
}

static void directPoll(void) {
  if (directState == DIRECT_OFF || directState == DIRECT_DONE ||
      directState == DIRECT_FAILED)
    return;
  if (directState == DIRECT_WAIT_WIFI) {
    int association = Wifi_AssocStatus();
    if (association == ASSOCSTATUS_ASSOCIATED) {
      struct in_addr mask, dns1, dns2;
      Wifi_GetIPInfo(&hotspotGateway, &mask, &dns1, &dns2);
      if (!hotspotGateway.s_addr) {
        failDirect("Hotspot did not provide a gateway through DHCP.");
        return;
      }
      if (!(directReturnMode ? prepareDirectReturn() : prepareWalker())) {
        directState = DIRECT_FAILED;
        return;
      }
      beginConnect();
    } else if (association == ASSOCSTATUS_CANNOTCONNECT) {
      failDirect("Wi-Fi connection failed. Reconnect to the phone hotspot.");
    }
    return;
  }
  if (directState == DIRECT_WAIT_PHONE) {
    if (directNow() >= deadline) beginConnect();
    return;
  }
  if (directState == DIRECT_CONNECTING) {
    struct sockaddr_in connected;
    socklen_t length = sizeof(connected);
    if (!getpeername(directSocket, (struct sockaddr *)&connected, &length)) {
      phoneAccepted();
    } else if (directNow() >= deadline) {
      waitForPhone();
    }
    return;
  }
  if (directState == DIRECT_SEND_ARM_HEADER) {
    unsigned remaining = WALKER_DIRECT_HEADER_SIZE - sentHeader;
    unsigned amount = remaining > DIRECT_CHUNK ? DIRECT_CHUNK : remaining;
    int n = send(directSocket, requestHeader + sentHeader, amount, 0);
    if (!n) {
      failDirect("Phone closed the connection before approving the direction.");
      return;
    }
    if (n > 0) {
      sentHeader += (unsigned)n;
      if (sentHeader == WALKER_DIRECT_HEADER_SIZE) {
        directState = DIRECT_READ_ARM_ACK;
        receivedHeader = 0;
        snprintf(statusText, sizeof(statusText),
                 "Direction requested. Waiting for approval in Connect to Console.");
      }
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    } else if (n < 0 && errno != EWOULDBLOCK && errno != EINTR) {
      failDirect("Wi-Fi stopped while requesting transfer approval.");
    } else if (directNow() >= deadline) {
      failDirect("Timed out waiting to request transfer approval.");
    }
    return;
  }
  if (directState == DIRECT_READ_ARM_ACK) {
    unsigned remaining = WALKER_DIRECT_HEADER_SIZE - receivedHeader;
    unsigned amount = remaining > DIRECT_CHUNK ? DIRECT_CHUNK : remaining;
    int n = recv(directSocket, responseHeader + receivedHeader, amount, 0);
    if (!n) {
      failDirect("Phone disconnected before approving the transfer direction.");
      return;
    }
    if (n > 0) {
      receivedHeader += (unsigned)n;
      if (receivedHeader == WALKER_DIRECT_HEADER_SIZE)
        validateArmResponseHeader();
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    } else if (n < 0 && errno != EWOULDBLOCK && errno != EINTR) {
      failDirect("Phone disconnected before approving the transfer direction.");
    } else if (directNow() >= deadline) {
      failDirect("Timed out waiting for Connect to Console approval.");
    }
    return;
  }
  if (directState == DIRECT_READ_ERROR) {
    unsigned total = walkerDirectBe32(responseHeader + 12);
    unsigned remaining = total - receivedError;
    unsigned amount = remaining > DIRECT_CHUNK ? DIRECT_CHUNK : remaining;
    int n = recv(directSocket, errorBody + receivedError, amount, 0);
    if (!n) {
      failDirect("Phone disconnected while explaining why it rejected the transfer.");
      return;
    }
    if (n > 0) {
      receivedError += (unsigned)n;
      if (receivedError == total) {
        if (walkerCrc(errorBody, total) !=
            walkerDirectBe32(responseHeader + 16)) {
          failDirect("Phone error response checksum failed.");
          return;
        }
        buildErrorStatus();
      }
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    } else if (n < 0 && errno != EWOULDBLOCK && errno != EINTR) {
      failDirect("Phone disconnected while explaining why it rejected the transfer.");
    } else if (directNow() >= deadline) {
      failDirect("Timed out reading the app's transfer rejection.");
    }
    return;
  }
  if (directReturnMode) {
    if (!transferAuthorized || directState != DIRECT_RETURNING) return;
    int result;
    if (returnStream.phase == WALKER_CONFIRM_DONE) {
      char error[160] = {0};
      WalkerLease lease;
      if (leaseInspect(selected, &lease) != 1 ||
          !leaseFinalizeDirectReturn(selected, lease.token, error,
                                     sizeof(error))) {
        failDirect(error[0] ? error
                            : "Phone confirmed; local finalization needs retry.");
        return;
      }
      closeSocket(0);
      directState = DIRECT_DONE;
      snprintf(statusText, sizeof(statusText),
               "Pokémon returned. SD copy verified and phone session closed.");
      if (onEvent) onEvent(2);
      return;
    }
    if (returnStream.phase == WALKER_PULL_DATA &&
        returnStream.sentData != lastReturnProgress) {
      lastReturnProgress = returnStream.sentData;
      snprintf(statusText, sizeof(statusText),
               "Receiving return: %lu / %u bytes.",
               (unsigned long)returnStream.sentData,
               WALKER_DIRECT_WALKER_SIZE);
    }
    if (directNow() >= deadline) {
      failDirect("Phone return timed out. Any staged recovery copy is kept.");
      return;
    }
    if (returnStream.phase == WALKER_CONFIRM_HEADER ||
        returnStream.phase == WALKER_CONFIRM_ACK) {
      result = walkerConfirmStep(&returnStream, &returnIo, 0,
                                 returnPayloadCrc);
    } else {
      result = walkerPullStep(&returnStream, &returnIo, 0,
                              &returnCrcState);
      if (returnStream.phase == WALKER_PULL_DONE)
        returnPayloadCrc = returnStream.durableSeq;
    }
    if (result < 0) {
      failDirect("Phone rejected or interrupted the return frame. The console remains locked.");
      return;
    }
    if (result > 0) {
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
      if (returnStream.phase == WALKER_PULL_DONE) {
        WalkerLease lease;
        char error[160] = {0};
        WalkerInfo info;
        char returnedTrainer[37];
        if (leaseInspect(selected, &lease) != 1 ||
            !walkerRead(payload, &info) || !walkerCanWalk(payload) ||
            !info.hasPokemon || !walkerTrainerKey(payload, returnedTrainer) ||
            strcmp(returnedTrainer, trainerKey) ||
            !leaseStageDirectReturn(selected, lease.token, payload,
                                    error, sizeof(error)) ||
            walkerConfirmBegin(&returnStream, sessionText,
                               returnPayloadCrc)) {
          failDirect(error[0] ? error
                              : "Return validation or durable SD staging failed. Phone copy is retained.");
          return;
        }
        directState = DIRECT_RETURNING;
        snprintf(statusText, sizeof(statusText),
                 "Pokémon saved to recovery staging. Confirming with phone.");
      } else if (returnStream.phase == WALKER_CONFIRM_DONE) {
        /* Finalization occurs at the top of the next poll, after the complete
         * OP_OK frame has been validated by walkerConfirmStep. */
        deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
      }
    }
    return;
  }
  if (directState == DIRECT_SEND_HEADER || directState == DIRECT_SEND_WALKER) {
    const unsigned char *data;
    unsigned remaining;
    if (directState == DIRECT_SEND_HEADER) {
      data = requestHeader + sentHeader;
      remaining = WALKER_DIRECT_HEADER_SIZE - sentHeader;
    } else {
      data = payload + sentPayload;
      remaining = WALKER_DIRECT_WALKER_SIZE - sentPayload;
    }
    unsigned amount = remaining > DIRECT_CHUNK ? DIRECT_CHUNK : remaining;
    int n = send(directSocket, data, amount, 0);
    if (!n) {
      failDirect("Phone closed the connection while receiving the walker.");
      return;
    }
    if (n > 0) {
      if (directState == DIRECT_SEND_HEADER) {
        sentHeader += (unsigned)n;
        if (sentHeader == WALKER_DIRECT_HEADER_SIZE)
          directState = DIRECT_SEND_WALKER;
      } else {
        sentPayload += (unsigned)n;
        if ((sentPayload & 0x1fffu) == 0 ||
            sentPayload == WALKER_DIRECT_WALKER_SIZE)
          snprintf(statusText, sizeof(statusText),
                   "Sending Pokémon: %u / %u bytes.", sentPayload,
                   WALKER_DIRECT_WALKER_SIZE);
        if (sentPayload == WALKER_DIRECT_WALKER_SIZE) {
          directState = DIRECT_READ_HEADER;
          snprintf(statusText, sizeof(statusText),
                   "Walker sent. Waiting for the app to verify and save it.");
        }
      }
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    } else if (n < 0 && errno != EWOULDBLOCK && errno != EINTR) {
      failDirect("Wi-Fi stopped while sending. Retry DSi Sync.");
    } else if (directNow() >= deadline) {
      failDirect("Timed out sending to the phone. Recovery copy is kept.");
    }
    return;
  }
  if (directState == DIRECT_READ_HEADER) {
    unsigned char *buffer = responseHeader + receivedHeader;
    unsigned total = WALKER_DIRECT_HEADER_SIZE;
    unsigned offset = receivedHeader;
    unsigned remaining = total - offset;
    unsigned amount = remaining > DIRECT_CHUNK ? DIRECT_CHUNK : remaining;
    int n = recv(directSocket, buffer, amount, 0);
    if (!n) {
      failDirect("Phone disconnected before acknowledging the transfer.");
      return;
    }
    if (n > 0) {
      if (directState == DIRECT_READ_HEADER) {
        receivedHeader += (unsigned)n;
        if (receivedHeader == WALKER_DIRECT_HEADER_SIZE)
          validateResponseHeader();
      }
      deadline = directNow() + DIRECT_IO_TIMEOUT_MS;
    } else if (n < 0 && errno != EWOULDBLOCK && errno != EINTR) {
      failDirect("Phone disconnected before acknowledging the transfer.");
    } else if (directNow() >= deadline) {
      failDirect("Timed out waiting for the phone acknowledgement.");
    }
  }
}

int syncStart(const char *path, SyncBeforeCheckout before, SyncEvent event) {
  WalkerLease existing;
  if (leaseInspect(path, &existing) == 1 && !existing.direct)
    return syncStartLegacy(path, before, event);
  syncStop();
  directMode = 1;
  directReturnMode = 0;
  directState = DIRECT_WAIT_WIFI;
  beforeCheckout = before;
  onEvent = event;
  snprintf(selected, sizeof(selected), "%s", path);
  snprintf(endpoint, sizeof(endpoint), "Auto TCP 30821");
  snprintf(statusText, sizeof(statusText),
           "Joining saved Wi-Fi. Arm Connect to Console in the app.");
  if (!ndsWifiConnectSaved()) {
    failDirect("No saved Wi-Fi connection. Configure the hotspot in Settings.");
    return 0;
  }
  return 1;
}

int syncStartReturn(const char *path, SyncEvent event) {
#ifdef __NDS__
  WalkerLease lease;
  int locked = leaseInspect(path, &lease);
  if (locked == 1 && lease.direct && !lease.revoked) {
    syncStop();
    directMode = 1;
    directReturnMode = 1;
    directState = DIRECT_WAIT_WIFI;
    onEvent = event;
    snprintf(selected, sizeof(selected), "%s", path);
    snprintf(endpoint, sizeof(endpoint), "Auto TCP 30821");
    snprintf(statusText, sizeof(statusText),
             "Joining Wi-Fi. Arm Connect to Console in the app.");
    if (!ndsWifiConnectSaved()) {
      failDirect("No saved Wi-Fi connection. Configure the hotspot in Settings.");
      return 0;
    }
    return 1;
  }
  if (locked == 1 && lease.direct && lease.revoked) {
    syncStop();
    directMode = 1;
    directState = DIRECT_FAILED;
    directReturnMode = 1;
    snprintf(endpoint, sizeof(endpoint), "Auto TCP 30821");
    snprintf(statusText, sizeof(statusText),
             "This phone session was revoked. Restore its recovery snapshot first.");
    return 0;
  }
  if (locked == 1) {
    syncStop();
    directMode = 0;
    directReturnMode = 0;
    return legacySyncStart(path, 0, event);
  }
  syncStop();
  directMode = 1;
  directState = DIRECT_FAILED;
  directReturnMode = 1;
  snprintf(endpoint, sizeof(endpoint), "Auto TCP 30821");
  snprintf(statusText, sizeof(statusText),
           locked < 0
               ? "Phone lock metadata is damaged. Use recovery before returning."
               : "No active phone checkout exists for this walker.");
  return 0;
#else
  return syncStartLegacy(path, 0, event);
#endif
}

#else
static int directMode;
#endif

int syncStartLegacy(const char *path, SyncBeforeCheckout before, SyncEvent event) {
#ifdef __NDS__
  WalkerLease existing;
  if (leaseInspect(path, &existing) == 1 && existing.direct) {
    syncStop();
    directMode = 1;
    directState = DIRECT_FAILED;
    snprintf(endpoint, sizeof(endpoint), "Auto TCP 30821");
    snprintf(statusText, sizeof(statusText),
             "Direct checkout is pending. Retry Auto sync with the same session.");
    return 0;
  }
#endif
  syncStop();
  directMode = 0;
#ifdef __NDS__
  directReturnMode = 0;
#endif
  return legacySyncStart(path, before, event);
}

int syncStartRecovery(const char *path, const unsigned char *baseline,
                      SyncEvent event) {
  syncStop();
  directMode = 0;
#ifdef __NDS__
  directReturnMode = 0;
#endif
  return legacySyncStartRecovery(path, baseline, event);
}

#ifndef __NDS__
int syncStart(const char *path, SyncBeforeCheckout before, SyncEvent event) {
  return syncStartLegacy(path, before, event);
}
#endif

void syncStop(void) {
#ifdef __NDS__
  if (directMode) closeSocket(1);
  directState = DIRECT_OFF;
  directReturnMode = 0;
#endif
  directMode = 0;
  legacySyncStop();
}

void syncPoll(void) {
#ifdef __NDS__
  if (directMode) directPoll();
  else
#endif
    legacySyncPoll();
}

int syncBusy(void) {
#ifdef __NDS__
  if (directMode)
    return directState != DIRECT_OFF && directState != DIRECT_DONE &&
           directState != DIRECT_FAILED;
#endif
  return legacySyncBusy();
}

const char *syncAddress(void) {
#ifdef __NDS__
  if (directMode) return endpoint;
#endif
  snprintf(legacyEndpoint, sizeof(legacyEndpoint), "%s:%u",
           legacySyncAddress(), WALKER_SYNC_PORT);
  return legacyEndpoint;
}

const char *syncStatus(void) {
#ifdef __NDS__
  if (directMode) return statusText;
#endif
  return legacySyncStatus();
}
