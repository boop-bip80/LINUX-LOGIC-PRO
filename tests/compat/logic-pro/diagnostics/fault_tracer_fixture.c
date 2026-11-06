/* Native sacrificial processes for the diagnostic observer tests.
 *
 * All commands arrive on an inherited pipe. No PID is accepted from input and
 * no signal is sent to another process. Only this process disables core dumps.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>

static volatile unsigned char *guard_page;
static int worker_gate[2];
static int worker_ready[2];
static int worker_exists;
static pthread_t worker;
static sigjmp_buf recovery;
static volatile sig_atomic_t recover_active;
static volatile sig_atomic_t recover_count;
static volatile sig_atomic_t trap_count;

static void fail(const char *message) {
    perror(message);
    _exit(90);
}

static int get_command(int fd) {
    unsigned char value;
    ssize_t size;
    do {
        size = read(fd, &value, 1);
    } while (size < 0 && errno == EINTR);
    if (size < 0)
        fail("read command");
    return size == 1 ? value : -1;
}

static void send_byte(int fd, char value) {
    ssize_t size;
    do {
        size = write(fd, &value, 1);
    } while (size < 0 && errno == EINTR);
    if (size != 1)
        fail("write control");
}

/* Keep signal handlers restricted to async-signal-safe operations. */
static void trap_handler(int signal_number) {
    (void)signal_number;
    ++trap_count;
    if (write(STDOUT_FILENO, "TRAP\n", 5) != 5)
        _exit(91);
}

static void recover_handler(int signal_number) {
    (void)signal_number;
    if (!recover_active)
        _exit(92);
    ++recover_count;
    if (write(STDOUT_FILENO, "SEGV\n", 5) != 5)
        _exit(93);
    siglongjmp(recovery, 1);
}

static void fatal_handler(int signal_number) {
    (void)signal_number;
    if (write(STDOUT_FILENO, "FATAL_HANDLER\n", 14) != 14)
        _exit(94);
    /* SA_RESETHAND makes the repeated synchronous fault terminate normally. */
}

__attribute__((noinline)) static void fault_page(void) {
    *guard_page = 0x7b;
}

static void *worker_main(void *unused) {
    (void)unused;
    printf("WORKER %ld\n", syscall(SYS_gettid));
    send_byte(worker_ready[1], 'R');
    for (;;) {
        int command = get_command(worker_gate[0]);
        if (command < 0 || command == 'Q')
            return NULL;
        if (command == 'F') {
            printf("FAULTING %ld\n", syscall(SYS_gettid));
            fault_page();
            _exit(95);
        }
        _exit(96);
    }
}

static void start_worker(void) {
    if (worker_exists)
        _exit(97);
    if (pthread_create(&worker, NULL, worker_main, NULL) != 0)
        fail("pthread_create");
    if (get_command(worker_ready[0]) != 'R')
        _exit(98);
    worker_exists = 1;
}

static void stop_worker(void) {
    if (!worker_exists)
        return;
    send_byte(worker_gate[1], 'Q');
    if (pthread_join(worker, NULL) != 0)
        fail("pthread_join");
    worker_exists = 0;
}

static void *short_lived_worker(void *unused) {
    return unused;
}

static void churn_threads(void) {
    pthread_t threads[8];
    for (size_t i = 0; i < sizeof(threads) / sizeof(threads[0]); ++i)
        if (pthread_create(&threads[i], NULL, short_lived_worker, NULL) != 0)
            fail("churn pthread_create");
    for (size_t i = 0; i < sizeof(threads) / sizeof(threads[0]); ++i)
        if (pthread_join(threads[i], NULL) != 0)
            fail("churn pthread_join");
    puts("CHURNED");
}

int main(int argc, char **argv) {
    if (argc != 2)
        return 89;
    const int recoverable = strcmp(argv[1], "recover") == 0;
    const int handled_fatal = strcmp(argv[1], "fatal") == 0;
    if (!recoverable && !handled_fatal && strcmp(argv[1], "existing") != 0
            && strcmp(argv[1], "late") != 0)
        return 88;
    const struct rlimit no_core = {0, 0};
    if (setrlimit(RLIMIT_CORE, &no_core) != 0)
        fail("setrlimit");
    if (prctl(PR_SET_DUMPABLE, 1L, 0L, 0L, 0L) != 0)
        fail("PR_SET_DUMPABLE");
    /* EINVAL is expected when the optional Yama LSM is not enabled. Actual
     * SEIZE/capture remains mandatory in the observer tests. */
    if (prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0L, 0L, 0L) != 0
            && errno != EINVAL)
        fail("PR_SET_PTRACER");
    alarm(40); /* A failed harness cannot leave this test child indefinitely. */
    setvbuf(stdout, NULL, _IONBF, 0);
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_handler = trap_handler;
    if (sigaction(SIGTRAP, &action, NULL) != 0)
        fail("sigaction SIGTRAP");
    if (recoverable || handled_fatal) {
        action.sa_handler = recoverable ? recover_handler : fatal_handler;
        action.sa_flags = recoverable ? 0 : SA_RESETHAND;
        if (sigaction(SIGSEGV, &action, NULL) != 0)
            fail("sigaction SIGSEGV");
    }
    const long page_size = sysconf(_SC_PAGESIZE);
    if (page_size <= 0)
        return 87;
    void *page = mmap(NULL, (size_t)page_size, PROT_NONE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (page == MAP_FAILED)
        fail("mmap");
    guard_page = page;
    if (pipe(worker_gate) != 0 || pipe(worker_ready) != 0)
        fail("pipe");
    if (strcmp(argv[1], "existing") == 0 || handled_fatal)
        start_worker();
    printf("READY %ld %ld 0x%" PRIxPTR " %ld\n",
           (long)getpid(), syscall(SYS_gettid), (uintptr_t)page, page_size);
    for (;;) {
        int command = get_command(STDIN_FILENO);
        if (command < 0 || command == 'Q') {
            stop_worker();
            puts("EXITING 37");
            return 37;
        }
        switch (command) {
        case 'T':
            if (raise(SIGTRAP) != 0)
                fail("raise SIGTRAP");
            printf("TRAP_RETURN %d\n", (int)trap_count);
            break;
        case 'F':
            if (!worker_exists)
                return 86;
            send_byte(worker_gate[1], 'F');
            break;
        case 'C':
            start_worker();
            break;
        case 'X':
            stop_worker();
            puts("WORKER_EXITED");
            break;
        case 'B':
            churn_threads();
            break;
        case 'R':
            if (!recoverable)
                return 85;
            recover_active = 1;
            if (sigsetjmp(recovery, 1) == 0)
                fault_page();
            recover_active = 0;
            printf("RECOVERED %d\n", (int)recover_count);
            break;
        case 'P':
            puts("PONG");
            break;
        case 'S':
            puts("STOPPING");
            if (raise(SIGSTOP) != 0)
                fail("raise SIGSTOP");
            puts("RESUMED");
            break;
        default:
            return 84;
        }
    }
}
