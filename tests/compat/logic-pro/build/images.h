#ifndef P003_IMAGES_H
#define P003_IMAGES_H
#include <dlfcn.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <string.h>

/* Pair the installed-binary hash audit with observation of dyld's actual
 * loaded paths. dlopen success alone does not satisfy the gate. */
static int p003_framework_images(void) {
    static const char *names[] = {
        "AppKit", "Foundation", "CoreGraphics", "CoreText", "ImageIO",
        "QuartzCore", "AudioToolbox"
    };
    static const char *versions[] = { "C", "C", "A", "A", "A", "A", "A" };
    for (unsigned n = 0; n < sizeof(names) / sizeof(names[0]); ++n) {
        char expected[256];
        snprintf(expected, sizeof(expected),
            "/System/Library/Frameworks/%s.framework/Versions/%s/%s",
            names[n], versions[n], names[n]);
        void *handle = dlopen(expected, RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            fprintf(stderr, "P003_IMAGE_ERROR %s: %s\n", names[n], dlerror());
            return 30;
        }
        unsigned matches = 0;
        for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
            const char *path = _dyld_get_image_name(i);
            if (!path) {
                fputs("P003_IMAGE_ERROR null image name\n", stderr);
                return 31;
            }
            const char *leaf = strrchr(path, '/');
            /* A competing Mach-O image may carry the framework's basename
             * without living under a .framework directory (e.g. dev-stubs).
             * Compare image identity before testing the authorized path. */
            if (leaf && strcmp(leaf + 1, names[n]) == 0) {
                if (strcmp(path, expected) != 0) {
                    fprintf(stderr, "P003_IMAGE_ERROR competing path %s\n", path);
                    return 32;
                }
                ++matches;
            }
        }
        if (matches != 1) {
            fprintf(stderr, "P003_IMAGE_ERROR %s count=%u\n", names[n], matches);
            return 33;
        }
        printf("P003_IMAGE %s\n", expected);
        /* Keep handles alive through GUI execution; closing them here would
         * remove the very loaded-image state this probe is qualifying. */
    }
    fflush(stdout);
    return 0;
}
#endif
