# Preserve the exact pinned libxpc gitlink, build options and other sources.
# The only replacement is the reached transaction.m source with a root-owned
# bridge to the existing liblaunch transaction lifecycle implementation.
function(darling_replace_libxpc_transaction target replacement)
    if(NOT TARGET "${target}" OR NOT IS_ABSOLUTE "${replacement}" OR NOT EXISTS "${replacement}")
        message(FATAL_ERROR "libxpc transaction bridge target/replacement missing")
    endif()
    get_target_property(source_dir "${target}" SOURCE_DIR)
    get_target_property(original "${target}" SOURCES)
    if(NOT source_dir OR NOT original)
        message(FATAL_ERROR "Pinned libxpc source inventory missing")
    endif()
    set(updated)
    set(count 0)
    foreach(source IN LISTS original)
        if(source STREQUAL "src/transaction.m" OR
           source STREQUAL "${source_dir}/src/transaction.m")
            math(EXPR count "${count} + 1")
            list(APPEND updated "${replacement}")
        elseif(source MATCHES "^\\$<" OR IS_ABSOLUTE "${source}")
            list(APPEND updated "${source}")
        else()
            # Property updates from the caller directory must not rebase the
            # pinned target's original relative source paths.
            list(APPEND updated "${source_dir}/${source}")
        endif()
    endforeach()
    if(NOT count EQUAL 1)
        message(FATAL_ERROR "Expected exactly one pinned libxpc src/transaction.m")
    endif()
    set_property(TARGET "${target}" PROPERTY SOURCES "${updated}")
endfunction()
