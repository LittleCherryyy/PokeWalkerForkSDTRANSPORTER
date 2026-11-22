/* V7.1 DSi Android-hotspot PING diagnostic, derived from V6.7 standalone harness.
 * Copyright remains with original SD Transporter / dependencies' authors.
 * GPL-3.0-or-later. RAM-only: does not read saves, ROM or .walker files.
 * This is NOT an in-game Nintendo DSi transport.
 */
#include <nds.h>
#include <dswifi9.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "direct_ping.h"

static char dsip[20], gwip[20];
static uint32_t gateway;
static const char *stage="pronto";
static int code=0, sockerr=0;
static int runs=0, successes=0, failures=0;
static bool heldLatch=false;

static void display(void) {
    consoleClear();
    iprintf("POKEWALKER V7.1 HOTSPOT\n");
    iprintf("--------------------------\n");
    iprintf("DSi IP: %s\n",dsip);
    iprintf("Gateway: %s\n",gwip);
    iprintf("Android (gateway): %s\n",gwip);
    iprintf("--------------------------\n");
    iprintf("IP automatico pelo DHCP\n");
    iprintf("Hotspot Android 2.4 GHz\n");
    iprintf("B: PING Android :30821\n");
    iprintf("X: eco RAM 2KB (op 5)\n");
    iprintf("START: sair\n");
    iprintf("--------------------------\n");
    iprintf("Fase: %.23s\n",stage);
    iprintf("Codigo: %d socket:%d\n",code,sockerr);
    iprintf("PING OK: %d\n",pw_direct_request_count());
    iprintf("ECO OK: %lu bytes\n",(unsigned long)pw_direct_echo_bytes());
    iprintf("Tentativas:%d OK:%d falhas:%d\n",runs,successes,failures);
    iprintf("SEM ACESSO AO SAVE\n");
}

static void progress(const char *name, int c, int se) {
    stage=name;code=c;sockerr=se;display();
}

int main(void) {
    consoleDemoInit();
    iprintf("V7.1 HOTSPOT: conectando\n");
    if(!Wifi_InitDefault(WFC_CONNECT)){
        iprintf("Falha WiFi; START sai\n");
        while(1){swiWaitForVBlank();scanKeys();if(keysDown()&KEY_START)return 1;}
    }
    struct in_addr gw,mask,dns1,dns2;
    struct in_addr ip=Wifi_GetIPInfo(&gw,&mask,&dns1,&dns2);
    snprintf(dsip,sizeof(dsip),"%s",inet_ntoa(ip));
    snprintf(gwip,sizeof(gwip),"%s",inet_ntoa(gw));
    gateway=gw.s_addr;
    display();

    while(1) {
        swiWaitForVBlank();
        scanKeys();
        uint32_t keys=keysHeld();
        if(keys&KEY_START)break;
        uint32_t actions=keys&(KEY_B|KEY_X);
        if(!actions){heldLatch=false;continue;}
        if(heldLatch)continue;
        heldLatch=true;
        if(!gateway){stage="Gateway DHCP nao disponivel";display();continue;}
        if(actions&(KEY_B|KEY_X)) {
            int rc;
            ++runs;
            if(actions&KEY_B)rc=pw_direct_ping_persistent(gateway,progress);
            else rc=pw_direct_echo_persistent(gateway,2048u,progress);
            sockerr=pw_direct_socket_errno();
            code=rc;
            if(rc==0){++successes;stage="OP_OK validado";}
            else{++failures;stage="ERRO: reinicie o DSi";}
        }
        display();
    }
    /* Intentionally no close() due to a previously observed libdswifi hang.
     * Quitting homebrew or restarting the DSi clears the test connection. */
    Wifi_DisconnectAP();
    return 0;
}
