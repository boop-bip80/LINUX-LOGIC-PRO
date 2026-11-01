# The pinned objc4 CMake directory enables OBJC_IS_DEBUG_BUILD unconditionally,
# although objc-config.h derives DEBUG from NDEBUG. Adapt the dependency's
# definition to Darling's selected build configuration without changing its
# runtime consistency assertion or adding contradictory compiler definitions.
function(darling_configure_objc_runtime runtime_directory)
    get_directory_property(objc_definitions DIRECTORY "${runtime_directory}" COMPILE_DEFINITIONS)
    list(FIND objc_definitions "OBJC_IS_DEBUG_BUILD=1" debug_definition)
    if(debug_definition EQUAL -1)
        message(FATAL_ERROR "Pinned objc4 debug definition changed; review darling_configure_objc_runtime")
    endif()
    list(REMOVE_ITEM objc_definitions "OBJC_IS_DEBUG_BUILD=1")
    list(APPEND objc_definitions
        "OBJC_IS_DEBUG_BUILD=$<IF:$<OR:$<CONFIG:Release>,$<CONFIG:RelWithDebInfo>,$<CONFIG:MinSizeRel>>,0,1>")
    set_property(DIRECTORY "${runtime_directory}" PROPERTY COMPILE_DEFINITIONS "${objc_definitions}")
endfunction()
