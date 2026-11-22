/* PokeWalker DSi V6.7: 30821 persistent echo transfer, RAM-only. */
#include <nds.h>
#include <dswifi9.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include "direct_ping.h"
#include "uplink.h"

static char ipstr[20],hotspotstr[20];
static uint32_t hotspotip;
static const char *phase="--",*event="Pronto";
static int code=0,sockerr=0;
static unsigned keys_count=0,good=0,bad=0;
static bool latch=false;
static void render(void){
    consoleClear();
    iprintf("POKEWALKER DSi V6.7 ECHO\n");
    iprintf("--------------------------\n");
    iprintf("IP: %s\nAndroid: %s\n",ipstr,hotspotstr);
    iprintf("B/Y: 30821 PING (reutiliza)\n");
    iprintf("A/X: V5 30822 (legado)\n");
    iprintf("L+A: eco 2KB; L+X: eco 8KB\n");
    iprintf("X: V5 30822 8192 bytes\n");
    iprintf("--------------------------\n");
    iprintf("Evento: %.24s\n",event);
    iprintf("Codigo: %d sock:%d\n",code,sockerr);
    iprintf("Fase: %.24s\n",phase);
    iprintf("PINGs OK: %d\n",pw_direct_request_count());
    iprintf("Eco OK: %lu blocos %lu B\n",(unsigned long)pw_direct_echo_blocks(),(unsigned long)pw_direct_echo_bytes());
    iprintf("Conexao viva: %s\n",pw_direct_connection_alive()?"SIM":"NAO");
    iprintf("Comandos:%lu OK:%lu Falhas:%lu\n",(unsigned long)keys_count,(unsigned long)good,(unsigned long)bad);
    iprintf("START: sair / reiniciar DSi\n");
    iprintf("SEM ACESSO AO SAVE\n");
}
static void on_stage(const char *p,int c,int se){phase=p;code=c;sockerr=se;render();}
int main(void){
    consoleDemoInit();iprintf("V6.6 PERSIST: conectando Wifi...\n");
    if(!Wifi_InitDefault(WFC_CONNECT)){
        iprintf("Falha Wifi_InitDefault\n");
        for(;;){swiWaitForVBlank();scanKeys();if(keysDown()&KEY_START)return 1;}
    }
    struct in_addr gw,mask,d1,d2;
    struct in_addr ip=Wifi_GetIPInfo(&gw,&mask,&d1,&d2);
    snprintf(ipstr,sizeof(ipstr),"%s",inet_ntoa(ip));
    hotspotip=gw.s_addr;
    snprintf(hotspotstr,sizeof(hotspotstr),"%s",inet_ntoa(gw));
    render();
    while(1){
        swiWaitForVBlank();scanKeys();
        unsigned held=keysHeld();
        if(held&KEY_START)break;
        unsigned cmd=held&(KEY_B|KEY_Y|KEY_A|KEY_X);
        if(!cmd){latch=false;continue;}
        if(latch)continue;
        latch=true;keys_count++;event="Comando reconhecido";render();
        int e;
        if((held&KEY_L) && (cmd&(KEY_A|KEY_X))){
            e=pw_direct_echo_persistent(hotspotip,(cmd&KEY_X)?8192u:2048u,on_stage);
            sockerr=pw_direct_socket_errno();
            event=e==0?"ECO 30821 CRC OK":"ECO 30821 falhou";
        }else if(cmd&(KEY_B|KEY_Y)){
            e=pw_direct_ping_persistent(hotspotip,on_stage);
            sockerr=pw_direct_socket_errno();
            event=e==0?"DIRECT OP_OK":"DIRECT falhou";
        }else{
            /* Testes legados mantidos; ainda usam sockets individuais. */
            e=pw_uplink_transfer(hotspotip,(cmd&KEY_X)?8192:2048);
            event=e==0?"V5 transfer OK":"V5 transfer falhou";
            phase=e==0?"V5 concluido":"V5 falhou";
        }
        code=e;if(e==0)good++;else bad++;
        render();
    }
    /* DSWifi close() em 30821 bloqueou na V6.4. Sessao TCP fica
       intencionalmente aberta. Reiniciar o console entre os testes. */
    Wifi_DisconnectAP();return 0;
}
