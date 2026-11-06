# Older objc4 pins enable OBJC_IS_DEBUG_BUILD unconditionally. Adapt that
# definition without changing the runtime assertion. The currently pinned
# runtime derives the macro from DEBUG itself; preserve its NDEBUG semantics
# instead of injecting a build-configuration guess over the header definition.
function(darling_configure_objc_runtime runtime_directory)
    get_directory_property(objc_definitions DIRECTORY "${runtime_directory}" COMPILE_DEFINITIONS)
    set(debug_definitions "${objc_definitions}")
    list(FILTER debug_definitions INCLUDE REGEX "^OBJC_IS_DEBUG_BUILD($|=)")
    if("${debug_definitions}" STREQUAL "")
        if(NOT EXISTS "${runtime_directory}/objc-config.h")
            message(FATAL_ERROR "Pinned objc4 debug configuration header is missing")
        endif()
        file(STRINGS "${runtime_directory}/objc-config.h" derived_definition
            REGEX "^[ \t]*#[ \t]*define[ \t]+OBJC_IS_DEBUG_BUILD[ \t]+DEBUG[ \t]*$")
        list(LENGTH derived_definition derived_count)
        if(NOT derived_count EQUAL 1)
            message(FATAL_ERROR "Pinned objc4 debug definition changed; review darling_configure_objc_runtime")
        endif()
        return()
    endif()
    if(NOT "${debug_definitions}" STREQUAL "OBJC_IS_DEBUG_BUILD=1")
        message(FATAL_ERROR "Pinned objc4 debug definition changed; review darling_configure_objc_runtime")
    endif()
    list(REMOVE_ITEM objc_definitions "OBJC_IS_DEBUG_BUILD=1")
    list(APPEND objc_definitions
        "OBJC_IS_DEBUG_BUILD=$<IF:$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>,0,1>")
    set_property(DIRECTORY "${runtime_directory}" PROPERTY COMPILE_DEFINITIONS "${objc_definitions}")
endfunction()
