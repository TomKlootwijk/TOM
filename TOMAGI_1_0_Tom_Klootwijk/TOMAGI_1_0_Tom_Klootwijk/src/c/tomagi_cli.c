#include "tomagi.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void usage(const char *name) {
    fprintf(stderr, "usage: %s PROGRAM.tmg [ticks] [--trace]\n", name);
}

int main(int argc, char **argv) {
    TomagiProgram program;
    TomagiState state;
    char error[256];
    uint32_t ticks;
    int trace = 0;
    uint32_t i;

    if (argc < 2 || argc > 4) {
        usage(argv[0]);
        return 2;
    }
    if (!tomagi_load_file(argv[1], &program, error, sizeof(error))) {
        fprintf(stderr, "tomagi: %s\n", error);
        return 1;
    }
    ticks = program.default_ticks;
    if (argc >= 3 && strcmp(argv[2], "--trace") != 0) {
        char *end = NULL;
        errno = 0;
        unsigned long value = strtoul(argv[2], &end, 0);
        if (errno || !end || *end || value > 0xfffffffful) {
            fprintf(stderr, "tomagi: invalid tick count\n");
            tomagi_free_program(&program);
            return 2;
        }
        ticks = (uint32_t)value;
    }
    if ((argc >= 3 && strcmp(argv[2], "--trace") == 0) ||
        (argc >= 4 && strcmp(argv[3], "--trace") == 0)) {
        trace = 1;
    }

    state = program.initial_state;
    state.cell = program.entry;
    for (i = 0; i < ticks && !(state.status & TOMAGI_STATUS_HALT); ++i) {
        uint32_t before = state.cell;
        const TomagiCell *cell = &program.cells[before];
        if (!tomagi_step(&program, &state)) {
            fprintf(stderr, "tomagi: execution error at step %u cell %u\n", i, before);
            tomagi_free_program(&program);
            return 1;
        }
        if (trace) {
            uint32_t key_hi, key_lo;
            tomagi_pack_key_contiguous(&state, &key_hi, &key_lo);
            fprintf(stderr,
                    "step=%" PRIu32 " cell_before=%" PRIu32 " opcode=%" PRIu32
                    " op_name=%s branch=%" PRIu32 " cell_after=%" PRIu32
                    " key_hi=%" PRIu32 " key_lo=%" PRIu32
                    " rho=%" PRId32 " theta=%" PRId32 " tick=%" PRId32
                    " phi=%" PRId32 " orientation=%" PRIu32 " sheet=%" PRIu32
                    " residual=%" PRId32 " output=%" PRIu32
                    " lineage=%" PRIu32 " status=%" PRIu32 "\n",
                    i, before, cell->opcode, tomagi_opcode_name(cell->opcode),
                    state.branch, state.cell, key_hi, key_lo,
                    state.rho, state.theta, state.tick, state.phi,
                    state.orientation, state.sheet, state.residual, state.output,
                    state.lineage, state.status);
        }
    }
    tomagi_print_state_json(stdout, &state);
    tomagi_free_program(&program);
    return 0;
}
