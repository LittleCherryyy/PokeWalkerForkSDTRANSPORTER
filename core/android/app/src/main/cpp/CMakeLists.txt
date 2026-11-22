cmake_minimum_required(VERSION 3.22)
project(pokewalker C)
# Avoid repeated CMake manifest regeneration in Windows builds. Re-run Gradle after editing CMake.
set(CMAKE_SUPPRESS_REGENERATION ON)
set(CMAKE_C_STANDARD 11)
set(SHARED ${CMAKE_CURRENT_LIST_DIR}/shared)
add_library(walker SHARED bridge.c ${SHARED}/walkerfile.c ${SHARED}/species.c ${SHARED}/walkerclassic.c)
target_include_directories(walker PRIVATE ${SHARED})
