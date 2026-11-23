#include <assert.h>
#include "walker_wifi_gate.h"
int main(void){
 WalkerWifiGate g;walkerWifiReset(&g);
 assert(!walkerWifiBegin(&g,0,1,3,100,20));
 assert(!walkerWifiBegin(&g,1,0,3,100,20));
 assert(walkerWifiBegin(&g,1,1,3,100,20));
 assert(!walkerWifiStep(&g,3,1,101,WALKER_WIFI_TRANSFERRING));
 assert(walkerWifiStep(&g,3,1,101,WALKER_WIFI_ASSOCIATING));
 assert(walkerWifiStep(&g,3,1,102,WALKER_WIFI_CONNECTED));
 assert(walkerWifiMayCall(&g,3,1,103));
 assert(!walkerWifiMayCall(&g,4,1,103));
 assert(!walkerWifiStep(&g,4,1,104,WALKER_WIFI_TRANSFERRING));
 assert(g.phase==WALKER_WIFI_ERROR);
 walkerWifiReset(&g);
 assert(walkerWifiBegin(&g,1,1,9,100,20));
 assert(!walkerWifiStep(&g,9,1,120,WALKER_WIFI_ASSOCIATING));
 walkerWifiReset(&g);
 assert(walkerWifiBegin(&g,1,1,9,100,20));
 walkerWifiCancel(&g);assert(!walkerWifiMayCall(&g,9,1,101));
 walkerWifiReset(&g);
 assert(walkerWifiBegin(&g,1,1,9,100,20));
 assert(walkerWifiStep(&g,9,1,101,WALKER_WIFI_ASSOCIATING));
 assert(walkerWifiStep(&g,9,1,102,WALKER_WIFI_CONNECTED));
 assert(walkerWifiStep(&g,9,1,103,WALKER_WIFI_TRANSFERRING));
 assert(walkerWifiStep(&g,9,1,104,WALKER_WIFI_SHUTDOWN));
 assert(walkerWifiStep(&g,9,1,105,WALKER_WIFI_DISABLED));
 return 0;
}
