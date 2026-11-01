# dyld must use chained fixups to rebase itself. The pinned ld64 cannot encode
# Clang's 32-bit relative switch lookup tables in a DYLD_CHAINED_PTR_64 image;
# libunwind's register-name switches otherwise introduce exactly those tables.
# Keep the switch behavior and dyld's chained fixups while preventing that
# compiler representation in the static unwind library linked into dyld.
function(darling_configure_static_unwind unwind_target)
    if(NOT TARGET "${unwind_target}")
        message(FATAL_ERROR "Pinned static libunwind target changed; review darling_configure_static_unwind")
    endif()
    get_target_property(unwind_type "${unwind_target}" TYPE)
    if(NOT unwind_type STREQUAL "STATIC_LIBRARY")
        message(FATAL_ERROR "Expected a static libunwind library; review darling_configure_static_unwind")
    endif()
    target_compile_options("${unwind_target}" PRIVATE
        "$<$<AND:$<COMPILE_LANGUAGE:CXX>,$<OR:$<CXX_COMPILER_ID:Clang>,$<CXX_COMPILER_ID:AppleClang>>>:-fno-jump-tables>")
endfunction()
