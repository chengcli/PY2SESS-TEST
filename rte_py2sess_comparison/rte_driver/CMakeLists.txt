cmake_minimum_required(VERSION 3.18)
project(py2sess_rte_driver LANGUAGES Fortran)

set(RTE_BUILD_DIR "$ENV{RTE_BUILD_DIR}" CACHE PATH "Existing rte-rrtmgp build directory")
if(NOT RTE_BUILD_DIR)
  get_filename_component(_default_rte_build "${CMAKE_CURRENT_LIST_DIR}/../../rte-rrtmgp/build-gpu" ABSOLUTE)
  set(RTE_BUILD_DIR "${_default_rte_build}" CACHE PATH "Existing rte-rrtmgp build directory" FORCE)
endif()

set(NETCDF_FORTRAN_PREFIX "$ENV{NETCDF_FORTRAN_PREFIX}" CACHE PATH "NetCDF-Fortran prefix")
if(NOT NETCDF_FORTRAN_PREFIX)
  set(NETCDF_FORTRAN_PREFIX "/tmp/netcdf-fortran-nv" CACHE PATH "NetCDF-Fortran prefix" FORCE)
endif()

if(CMAKE_Fortran_COMPILER_ID MATCHES "NVHPC|PGI")
  add_compile_options(-acc -Mfree)
  add_link_options(-acc)
  if(DEFINED ENV{NVFORTRAN_GPU_FLAGS})
    add_compile_options($ENV{NVFORTRAN_GPU_FLAGS})
    add_link_options($ENV{NVFORTRAN_GPU_FLAGS})
  else()
    add_compile_options(-gpu=cc120)
    add_link_options(-gpu=cc120)
  endif()
endif()

add_executable(rte_sw_py2sess rte_sw_py2sess.F90)
target_include_directories(
  rte_sw_py2sess
  PRIVATE
    "${RTE_BUILD_DIR}/modules"
    "${NETCDF_FORTRAN_PREFIX}/include"
)
target_link_directories(
  rte_sw_py2sess
  PRIVATE
    "${RTE_BUILD_DIR}/rte/frontend"
    "${NETCDF_FORTRAN_PREFIX}/lib"
)
target_link_libraries(rte_sw_py2sess PRIVATE rte netcdff netcdf)

