cmake_minimum_required(VERSION 3.20)
project(nhdf_ccd_reference VERSION 0.4.0 LANGUAGES CXX)

add_library(nhdf_ccd STATIC src/ccd.cpp)
target_include_directories(nhdf_ccd PUBLIC include)
target_compile_features(nhdf_ccd PUBLIC cxx_std_17)
target_compile_options(nhdf_ccd PRIVATE -Wall -Wextra -Wpedantic)

add_executable(nhdf_ccd_smoke tests/smoke.cpp)
target_link_libraries(nhdf_ccd_smoke PRIVATE nhdf_ccd)

enable_testing()
add_test(NAME nhdf_ccd_smoke COMMAND nhdf_ccd_smoke)
