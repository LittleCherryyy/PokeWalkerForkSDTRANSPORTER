/* Direct HGSS Pokémon checkout: resident ARM9 transaction coordinator.
 * GPL-3.0-or-later.
 *
 * The original SD Transporter IR hook stages a real Pokémon in a 64 KiB
 * virtual EEPROM. ARM7 writes and verifies it to SD; this code transmits
 * that SAME image to the Android app, without launching intermediary
 * homebrew. It never runs inside the virtual IR stub, VBlank or IRQ.
 *
 * No Wi-Fi/socket ABI is guessed. A platform-specific backend MUST provide
 * walkerDirectRadioBackend() with a verified nonblocking connection to the
 * Android phone (hotspot gateway) before this can transfer on real DSi.
 */
#include <nds.h>
#include "cardengine_header_arm9.h"
#include "walker_emu.h"
#include "walker_direct_bridge.h"
#include "walker_direct_radio.h"
#include "walker_push_stream.h"

#if !defined(TWLSDK) && !defined(B4DS) && !defined(DLDI) && !defined(GSDD)
extern cardengineArm9 * volatile ce9;

/* A missing backend is an explicit unsupported state, not false success. */
__attribute__((weak))
const WalkerDirectRadioOps *walkerDirectRadioBackend(void) { return 0; }

enum { WORKER_IDLE=0, WORKER_CONNECTING=1, WORKER_SENDING=2 };
static unsigned workerStage;
static unsigned workerBusy;
static WalkerPushStream stream;
static const WalkerDirectRadioOps *radio;
static WalkerControl *owner;

static int ioWrite(void *unused, const unsigned char *buf,unsigned size) {
    (void)unused;
    return radio && radio->write ? radio->write(buf,size) : -1;
}
static int ioRead(void *unused,unsigned char *buf,unsigned size) {
    (void)unused;
    return radio && radio->read ? radio->read(buf,size) : -1;
}
static const WalkerPushIo io={ioWrite,ioRead};

static void disconnect(void) {
    if(radio && radio->close) radio->close();
    workerStage=WORKER_IDLE;
    owner=0;
    radio=0;
}
static void retry(WalkerControl *c) {
    disconnect();
    if(!c || c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC) return;
    /* Never clear checkoutState or the durable SD recovery image. */
    if(c->direct.state==WALKER_DIRECT_PUSHING) {
        c->direct.state=WALKER_DIRECT_PUSH_READY;
        c->direct.error=WALKER_DIRECT_ERR_TRANSPORT;
        if(c->direct.attempts!=0xffffffffu)c->direct.attempts++;
    }
}
static int committed(const WalkerControl *c) {
    if(!c || c->magic!=WALKER_MAGIC || c->version!=WALKER_VERSION ||
       !c->cluster || !c->eeprom ||
       c->direct.magic!=WALKER_DIRECT_BRIDGE_MAGIC ||
       c->checkoutState!=WALKER_CHECKOUT_COMPLETE ||
       c->state || !c->writeSeq ||
       c->writeSeq!=c->flushedSeq ||
       c->direct.offeredSeq!=c->writeSeq ||
       c->direct.durableSeq!=c->writeSeq) return 0;
    for(unsigned i=0;i<WALKER_SECTORS;++i)
        if(c->dirty[i]) return 0;
    return 1;
}

/* Call from a synchronous game card read callback AFTER it finishes, and
 * only when CPSR is ordinary execution mode and IME is enabled.
 * Each invocation performs at most one nonblocking socket operation.
 * This callback may be too sparse for practical transfer; hardware/runtime
 * validation is still required to find a safe, sufficiently frequent site. */
void walkerDirectArm9Tick(void) {
    if(workerBusy) return; /* prevent reentry during radio callbacks */
    /* The virtual EEPROM lives in a game-reserved memory region and its
     * normal-MPU accessibility is NOT yet verified. With no verified
     * radio/memory backend, do not even dereference walkerControl from the
     * normal ARM9 card-read path. A future backend must prove the memory
     * mapping and coordinate cache maintenance before being linked. */
    if(workerStage==WORKER_IDLE) {
        const WalkerDirectRadioOps *probe=walkerDirectRadioBackend();
        if(!probe || !probe->available || probe->available()<=0) return;
    }
    workerBusy=1;
    cardengineArm9 *local=ce9;
    WalkerControl *c=local && local->walkerControl ?
                     (WalkerControl *)local->walkerControl : 0;
    /* The cardengine pointer can change on soft reset. Never dereference
     * an owner from the previous game after control validation fails. */
    if(!c || c->magic!=WALKER_MAGIC || c->version!=WALKER_VERSION) {
        if(workerStage!=WORKER_IDLE) disconnect();
        workerBusy=0;
        return;
    }
    if(workerStage!=WORKER_IDLE && owner!=c) {
        disconnect(); /* old owner may have been unmapped by reset */
        workerBusy=0;
        return;
    }
    if(!committed(c) ||
       (c->direct.state!=WALKER_DIRECT_PUSH_READY &&
        c->direct.state!=WALKER_DIRECT_PUSHING)) {
        if(workerStage!=WORKER_IDLE) retry(c);
        workerBusy=0;
        return;
    }
    if(workerStage==WORKER_IDLE) {
        if(c->direct.state!=WALKER_DIRECT_PUSH_READY) {
            workerBusy=0;
            return;
        }
        const WalkerDirectRadioOps *api=walkerDirectRadioBackend();
        if(!api || !api->available || !api->connect || !api->write ||
           !api->read || !api->close || api->available()<=0) {
            /* An absent Wi-Fi driver leaves Pokémon safe in the .walker. */
            workerBusy=0;
            return;
        }
        if(walkerPushBegin(&stream,(const unsigned char *)c->eeprom,
                c->writeSeq,c->direct.crc32,
                c->direct.session,c->direct.trainer)<0) {
            c->direct.error=WALKER_DIRECT_ERR_PROTOCOL;
            workerBusy=0;
            return;
        }
        owner=c;
        radio=api;
        workerStage=WORKER_CONNECTING;
        c->direct.state=WALKER_DIRECT_PUSHING;
    }

    if(workerStage==WORKER_CONNECTING) {
        const int status=radio->connect(WALKER_DIRECT_PORT);
        if(status<0) retry(c);
        else if(status>0) workerStage=WORKER_SENDING;
    } else if(workerStage==WORKER_SENDING) {
        const int result=walkerPushStep(&stream,&io,0,c->writeSeq);
        if(result<0) retry(c);
        else if(result>0) {
            /* Commit PHONE_OWNS ONLY after a complete, session-bound
             * Android OP_OK for the entire 64 KiB payload. */
            disconnect();
            c->direct.error=WALKER_DIRECT_ERR_NONE;
            c->direct.state=WALKER_DIRECT_PHONE_OWNS;
        }
    }
    workerBusy=0;
}

#else
void walkerDirectArm9Tick(void) {}
#endif
