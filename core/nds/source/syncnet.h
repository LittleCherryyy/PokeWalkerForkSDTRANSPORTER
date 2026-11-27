#ifndef WALKER_SYNCNET_H
#define WALKER_SYNCNET_H
#define WALKER_SYNC_PORT 30820
typedef int (*SyncBeforeCheckout)(void);
typedef void (*SyncEvent)(int); /* 1=checked out, 2=returned */
/* NDS: automatic client to Android DSi Sync via DHCP gateway:30821. */
int syncStart(const char *, SyncBeforeCheckout, SyncEvent);
/* On a direct phone checkout, pull the phone's current walker and confirm its
 * durable SD staging. Older HTTP leases keep their original listener flow. */
int syncStartReturn(const char *, SyncEvent);
/* Compatibility HTTP server on port 30820. */
int syncStartLegacy(const char *, SyncBeforeCheckout, SyncEvent);
int syncStartRecovery(const char *,const unsigned char *,SyncEvent);
void syncPoll(void);
void syncStop(void);
int syncBusy(void);
const char *syncAddress(void);
const char *syncStatus(void);
int legacySyncStart(const char *, SyncBeforeCheckout, SyncEvent);
int legacySyncStartRecovery(const char *, const unsigned char *, SyncEvent);
void legacySyncPoll(void);
void legacySyncStop(void);
int legacySyncBusy(void);
const char *legacySyncAddress(void);
const char *legacySyncStatus(void);
#endif
