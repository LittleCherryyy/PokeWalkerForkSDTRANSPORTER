#ifndef WALKER_WIFI_GATE_H
#define WALKER_WIFI_GATE_H
/* Host-testable lifecycle guard; no hardware or save access. */
#include <stdint.h>
typedef enum {
 WALKER_WIFI_DISABLED=0, WALKER_WIFI_INIT, WALKER_WIFI_ASSOCIATING,
 WALKER_WIFI_CONNECTED, WALKER_WIFI_TRANSFERRING, WALKER_WIFI_SHUTDOWN,
 WALKER_WIFI_ERROR
} WalkerWifiPhase;
typedef struct {
 WalkerWifiPhase phase;
 uint32_t required_overlay_generation, deadline_tick;
 uint8_t api_verified, overlay_resident, cancelled;
} WalkerWifiGate;
static inline void walkerWifiReset(WalkerWifiGate *g) {
 if(g) *g=(WalkerWifiGate){0};
}
static inline int walkerWifiBegin(WalkerWifiGate *g,int api,int resident,
 uint32_t generation,uint32_t now,uint32_t timeout) {
 if(!g||g->phase!=WALKER_WIFI_DISABLED||!api||!resident||!timeout||timeout>0x7fffffffU)return 0;
 g->api_verified=1;g->overlay_resident=1;g->cancelled=0;
 g->required_overlay_generation=generation;g->deadline_tick=now+timeout;
 g->phase=WALKER_WIFI_INIT;return 1;
}
static inline int walkerWifiMayCall(const WalkerWifiGate *g,uint32_t generation,
 int resident,uint32_t now) {
 return g&&g->api_verified&&g->overlay_resident&&resident&&!g->cancelled&&
 g->required_overlay_generation==generation&&
 (int32_t)(now-g->deadline_tick)<0&&
 g->phase>=WALKER_WIFI_INIT&&g->phase<=WALKER_WIFI_SHUTDOWN;
}
static inline int walkerWifiStep(WalkerWifiGate *g,uint32_t generation,
 int resident,uint32_t now,WalkerWifiPhase next) {
 if(!g||g->phase==WALKER_WIFI_DISABLED||g->phase==WALKER_WIFI_ERROR)return 0;
 if(!walkerWifiMayCall(g,generation,resident,now)){g->phase=WALKER_WIFI_ERROR;return 0;}
 int valid=(g->phase==WALKER_WIFI_INIT&&next==WALKER_WIFI_ASSOCIATING)||
 (g->phase==WALKER_WIFI_ASSOCIATING&&next==WALKER_WIFI_CONNECTED)||
 (g->phase==WALKER_WIFI_CONNECTED&&(next==WALKER_WIFI_TRANSFERRING||next==WALKER_WIFI_SHUTDOWN))||
 (g->phase==WALKER_WIFI_TRANSFERRING&&(next==WALKER_WIFI_CONNECTED||next==WALKER_WIFI_SHUTDOWN))||
 (g->phase==WALKER_WIFI_SHUTDOWN&&next==WALKER_WIFI_DISABLED);
 if(!valid)return 0;
 g->phase=next;if(next==WALKER_WIFI_DISABLED)walkerWifiReset(g);
 return 1;
}
static inline void walkerWifiCancel(WalkerWifiGate *g){
 if(g){g->cancelled=1;g->phase=WALKER_WIFI_ERROR;}
}
#endif
