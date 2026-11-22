/* Only PING/OK diagnostic framing, no in-game network transport yet. */
#ifndef WALKER_PING_RUNTIME_H
#define WALKER_PING_RUNTIME_H
unsigned walkerV71MakePing(void *output, unsigned output_capacity);
int walkerV71CheckPingOk(const void *frame, unsigned frame_bytes);
#endif
