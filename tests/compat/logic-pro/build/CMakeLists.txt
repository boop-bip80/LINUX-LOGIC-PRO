# This directory is added from src/CMakeLists.txt, after its Darwin compiler,
# headers, ld64, and genuine framework targets have been established.
if(NOT COMPONENT_gui OR NOT TARGET AppKit OR NOT TARGET Foundation)
    message(FATAL_ERROR "P003 probes require the real GUI and Foundation targets")
endif()
if(NOT TARGET_x86_64 OR TARGET_i386)
    message(FATAL_ERROR "P003 baseline probes require x86_64 only")
endif()

include(darling_exe)
add_darling_executable(p003_macho macho.c)
add_darling_executable(p003_foundation foundation.m)
target_compile_options(p003_foundation PRIVATE -fblocks -fobjc-exceptions)
target_include_directories(p003_foundation PRIVATE "${CMAKE_SOURCE_DIR}/src/launchd/liblaunch")
target_link_libraries(p003_foundation Foundation objc xpc launch)
add_darling_executable(p003_gui gui.m)
target_compile_options(p003_gui PRIVATE -fblocks -fobjc-exceptions)
target_link_libraries(p003_gui AppKit Foundation objc)

foreach(probe p003_macho p003_foundation p003_gui)
    target_compile_options(${probe} PRIVATE -fno-omit-frame-pointer)
    set_target_properties(${probe} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/p003-probes")
endforeach()
install(TARGETS p003_macho p003_foundation p003_gui
    DESTINATION libexec/darling/usr/libexec/p003 COMPONENT gui)
