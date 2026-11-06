#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* FNV-1a/32 is independently evaluated by the host. The runtime's result is
 * never used to generate an acceptance oracle. Volatile prevents the compiler
 * from replacing this computation with an embedded result. */
int main(int argc, char **argv) {
    if (argc != 2 || strlen(argv[1]) == 0 || strlen(argv[1]) > 64) {
        fputs("P003_MACHO_ERROR invalid arguments\n", stderr);
        return 64;
    }
    volatile uint32_t hash = UINT32_C(2166136261);
    const unsigned char *cursor = (const unsigned char *)argv[1];
    for (; *cursor; ++cursor) {
        hash ^= *cursor;
        hash *= UINT32_C(16777619);
    }
    printf("P003_MACHO nonce=%s hash=%08" PRIx32 "\n", argv[1], (uint32_t)hash);
    return 0;
}
