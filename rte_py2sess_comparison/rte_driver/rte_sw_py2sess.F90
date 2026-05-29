module mo_py2sess_gpt_fluxes
  use mo_rte_kind, only: wp, wl
  use mo_fluxes, only: ty_fluxes
  use mo_optical_props, only: ty_optical_props
  implicit none

  type, extends(ty_fluxes) :: ty_py2sess_gpt_fluxes
    real(wp), dimension(:,:,:), pointer :: flux_up => null()
    real(wp), dimension(:,:,:), pointer :: flux_dn => null()
    real(wp), dimension(:,:,:), pointer :: flux_net => null()
    real(wp), dimension(:,:,:), pointer :: flux_dn_dir => null()
  contains
    procedure :: reduce => reduce_gpt
    procedure :: are_desired => are_desired_gpt
  end type ty_py2sess_gpt_fluxes

contains
  function reduce_gpt(this, gpt_flux_up, gpt_flux_dn, spectral_disc, top_at_1, gpt_flux_dn_dir) result(error_msg)
    class(ty_py2sess_gpt_fluxes), intent(inout) :: this
    real(wp), dimension(:,:,:), intent(in) :: gpt_flux_up
    real(wp), dimension(:,:,:), intent(in) :: gpt_flux_dn
    class(ty_optical_props), intent(in) :: spectral_disc
    logical, intent(in) :: top_at_1
    real(wp), dimension(:,:,:), optional, intent(in) :: gpt_flux_dn_dir
    character(len=128) :: error_msg

    error_msg = ""
    !$acc update self(gpt_flux_up, gpt_flux_dn)
    if(present(gpt_flux_dn_dir)) then
      !$acc update self(gpt_flux_dn_dir)
    end if
    if(associated(this%flux_up)) this%flux_up(:,:,:) = gpt_flux_up(:,:,:)
    if(associated(this%flux_dn)) this%flux_dn(:,:,:) = gpt_flux_dn(:,:,:)
    if(associated(this%flux_net)) this%flux_net(:,:,:) = gpt_flux_dn(:,:,:) - gpt_flux_up(:,:,:)
    if(associated(this%flux_dn_dir) .and. present(gpt_flux_dn_dir)) then
      this%flux_dn_dir(:,:,:) = gpt_flux_dn_dir(:,:,:)
    end if
  end function reduce_gpt

  function are_desired_gpt(this)
    class(ty_py2sess_gpt_fluxes), intent(in) :: this
    logical :: are_desired_gpt

    are_desired_gpt = associated(this%flux_up) .or. associated(this%flux_dn) .or. &
                      associated(this%flux_net) .or. associated(this%flux_dn_dir)
  end function are_desired_gpt
end module mo_py2sess_gpt_fluxes

program rte_sw_py2sess
  use netcdf
  use mo_rte_kind, only: wp
  use mo_rte_config, only: rte_config_checks
  use mo_optical_props, only: ty_optical_props_2str
  use mo_rte_sw, only: rte_sw
  use mo_py2sess_gpt_fluxes, only: ty_py2sess_gpt_fluxes
  implicit none

  character(len=512) :: input_path, output_path, timing_path, arg
  integer :: repeats, warmups, iarg
  integer :: ncid, dimid, varid, status
  integer :: nlay, nlev, ngpt, ilay, igpt, rep, clock_rate, t0, t1
  real(wp) :: elapsed, best_s, mean_s, std_s, sum_s, sum2_s, mu0_scalar
  real(wp), allocatable :: tau_in(:,:), ssa_in(:,:), g_in(:,:)
  real(wp), allocatable :: albedo(:), fbeam(:), wavenumber(:)
  real(wp), allocatable :: band_lims_wvn(:,:), mu0(:), inc_flux(:,:)
  real(wp), allocatable :: sfc_alb_dir(:,:), sfc_alb_dif(:,:)
  integer, allocatable :: band_lims_gpt(:,:)
  real(wp), allocatable, target :: flux_up(:,:,:), flux_dn(:,:,:), flux_net(:,:,:), flux_dn_dir(:,:,:)
  type(ty_optical_props_2str) :: atmos
  type(ty_py2sess_gpt_fluxes) :: fluxes
  character(len=128) :: err

  input_path = "outputs/py2sess_uv_optics.nc"
  output_path = "outputs/rte_uv_fluxes.nc"
  timing_path = "outputs/rte_timings.csv"
  repeats = 5
  warmups = 1

  call rte_config_checks(.false._wl)

  iarg = 1
  do while(iarg <= command_argument_count())
    call get_command_argument(iarg, arg)
    select case(trim(arg))
    case("--input")
      iarg = iarg + 1
      call get_command_argument(iarg, input_path)
    case("--output")
      iarg = iarg + 1
      call get_command_argument(iarg, output_path)
    case("--timing")
      iarg = iarg + 1
      call get_command_argument(iarg, timing_path)
    case("--repeats")
      iarg = iarg + 1
      call get_command_argument(iarg, arg)
      read(arg, *) repeats
    case("--warmups")
      iarg = iarg + 1
      call get_command_argument(iarg, arg)
      read(arg, *) warmups
    case default
      write(*,*) "unknown argument: ", trim(arg)
      stop 2
    end select
    iarg = iarg + 1
  end do

  call check(nf90_open(trim(input_path), nf90_nowrite, ncid), "open input")
  call check(nf90_inq_dimid(ncid, "layer", dimid), "layer dim")
  call check(nf90_inquire_dimension(ncid, dimid, len=nlay), "layer len")
  call check(nf90_inq_dimid(ncid, "spectral", dimid), "spectral dim")
  call check(nf90_inquire_dimension(ncid, dimid, len=ngpt), "spectral len")
  nlev = nlay + 1

  allocate(tau_in(ngpt, nlay), ssa_in(ngpt, nlay), g_in(ngpt, nlay))
  allocate(albedo(ngpt), fbeam(ngpt), wavenumber(ngpt))
  call read_2d(ncid, "tau_scaled", tau_in)
  call read_2d(ncid, "ssa_scaled", ssa_in)
  call read_2d(ncid, "g_scaled", g_in)
  call read_1d(ncid, "albedo", albedo)
  call read_1d(ncid, "fbeam", fbeam)
  call read_1d(ncid, "wavenumber_cm_inv", wavenumber)
  call check(nf90_inq_varid(ncid, "mu0", varid), "mu0 var")
  call check(nf90_get_var(ncid, varid, mu0_scalar), "mu0 read")
  call check(nf90_close(ncid), "close input")

  allocate(band_lims_wvn(2, ngpt), band_lims_gpt(2, ngpt))
  do igpt = 1, ngpt
    band_lims_wvn(1, igpt) = max(wavenumber(igpt), 0._wp)
    band_lims_wvn(2, igpt) = max(wavenumber(igpt), 0._wp)
    band_lims_gpt(1, igpt) = igpt
    band_lims_gpt(2, igpt) = igpt
  end do

  err = atmos%alloc_2str(1, nlay, band_lims_wvn, band_lims_gpt, "py2sess UV optics")
  call stop_on_err(err)
  call atmos%set_top_at_1(.true.)
  do igpt = 1, ngpt
    do ilay = 1, nlay
      atmos%tau(1, ilay, igpt) = tau_in(igpt, ilay)
      atmos%ssa(1, ilay, igpt) = ssa_in(igpt, ilay)
      atmos%g  (1, ilay, igpt) = g_in  (igpt, ilay)
    end do
  end do

  allocate(mu0(1), inc_flux(1, ngpt), sfc_alb_dir(ngpt, 1), sfc_alb_dif(ngpt, 1))
  mu0(1) = mu0_scalar
  inc_flux(1, :) = fbeam(:)
  sfc_alb_dir(:, 1) = albedo(:)
  sfc_alb_dif(:, 1) = albedo(:)

  allocate(flux_up(1, nlev, ngpt), flux_dn(1, nlev, ngpt), flux_net(1, nlev, ngpt), flux_dn_dir(1, nlev, ngpt))
  fluxes%flux_up => flux_up
  fluxes%flux_dn => flux_dn
  fluxes%flux_net => flux_net
  fluxes%flux_dn_dir => flux_dn_dir

  do rep = 1, warmups
    err = rte_sw(atmos, mu0, inc_flux, sfc_alb_dir, sfc_alb_dif, fluxes)
    call stop_on_err(err)
  end do

  call system_clock(count_rate=clock_rate)
  best_s = huge(1._wp)
  sum_s = 0._wp
  sum2_s = 0._wp
  call write_timing_header(timing_path)
  do rep = 1, repeats
    call system_clock(t0)
    err = rte_sw(atmos, mu0, inc_flux, sfc_alb_dir, sfc_alb_dif, fluxes)
    call stop_on_err(err)
    call system_clock(t1)
    elapsed = real(t1 - t0, wp) / real(clock_rate, wp)
    best_s = min(best_s, elapsed)
    sum_s = sum_s + elapsed
    sum2_s = sum2_s + elapsed * elapsed
    call append_timing(timing_path, rep - 1, elapsed, ngpt, nlay)
  end do
  mean_s = sum_s / real(repeats, wp)
  std_s = sqrt(max(sum2_s / real(repeats, wp) - mean_s * mean_s, 0._wp))

  call write_output(trim(output_path), nlev, ngpt, flux_up(1,:,:), flux_dn(1,:,:), &
                    flux_net(1,:,:), flux_dn_dir(1,:,:), repeats, best_s, mean_s, std_s)
  write(*,'(a,1x,a,1x,a,f10.6)') "wrote", trim(output_path), "best_s", best_s

contains
  subroutine check(status_in, label)
    integer, intent(in) :: status_in
    character(len=*), intent(in) :: label
    if(status_in /= nf90_noerr) then
      write(*,*) trim(label), ": ", trim(nf90_strerror(status_in))
      stop 1
    end if
  end subroutine check

  subroutine stop_on_err(message)
    character(len=*), intent(in) :: message
    if(len_trim(message) > 0) then
      write(*,*) trim(message)
      stop 1
    end if
  end subroutine stop_on_err

  subroutine read_1d(ncid_in, name, values)
    integer, intent(in) :: ncid_in
    character(len=*), intent(in) :: name
    real(wp), intent(out) :: values(:)
    integer :: id
    call check(nf90_inq_varid(ncid_in, trim(name), id), trim(name)//" var")
    call check(nf90_get_var(ncid_in, id, values), trim(name)//" read")
  end subroutine read_1d

  subroutine read_2d(ncid_in, name, values)
    integer, intent(in) :: ncid_in
    character(len=*), intent(in) :: name
    real(wp), intent(out) :: values(:,:)
    integer :: id
    call check(nf90_inq_varid(ncid_in, trim(name), id), trim(name)//" var")
    call check(nf90_get_var(ncid_in, id, values), trim(name)//" read")
  end subroutine read_2d

  subroutine write_timing_header(path)
    character(len=*), intent(in) :: path
    integer :: unit
    open(newunit=unit, file=trim(path), status="replace", action="write")
    write(unit,'(a)') "engine,backend,device,dtype,repeat,seconds,rows,layers,rows_per_second,status,skip_reason"
    close(unit)
  end subroutine write_timing_header

  subroutine append_timing(path, repeat_index, seconds, rows, layers)
    character(len=*), intent(in) :: path
    integer, intent(in) :: repeat_index, rows, layers
    real(wp), intent(in) :: seconds
    integer :: unit
    open(newunit=unit, file=trim(path), status="old", position="append", action="write")
    write(unit,'(a,",",a,",",a,",",a,",",i0,",",es16.8,",",i0,",",i0,",",es16.8,",",a,",",a)') &
      "rte-rrtmgp", "rte-sw", "gpu", "float64", repeat_index, seconds, rows, layers, &
      real(rows, wp) / seconds, "ok", ""
    close(unit)
  end subroutine append_timing

  subroutine write_output(path, nlev_in, ngpt_in, up, dn, net, direct, nreps, best, mean, std)
    character(len=*), intent(in) :: path
    integer, intent(in) :: nlev_in, ngpt_in, nreps
    real(wp), intent(in) :: up(nlev_in, ngpt_in), dn(nlev_in, ngpt_in)
    real(wp), intent(in) :: net(nlev_in, ngpt_in), direct(nlev_in, ngpt_in)
    real(wp), intent(in) :: best, mean, std
    integer :: nc_out, dim_level, dim_spectral
    integer :: id_up, id_dn, id_net, id_direct

    call check(nf90_create(trim(path), nf90_clobber, nc_out), "create output")
    call check(nf90_def_dim(nc_out, "level", nlev_in, dim_level), "def level")
    call check(nf90_def_dim(nc_out, "spectral", ngpt_in, dim_spectral), "def spectral")
    call check(nf90_def_var(nc_out, "flux_up", nf90_double, [dim_level, dim_spectral], id_up), "def flux_up")
    call check(nf90_def_var(nc_out, "flux_down", nf90_double, [dim_level, dim_spectral], id_dn), "def flux_down")
    call check(nf90_def_var(nc_out, "flux_net_down_minus_up", nf90_double, [dim_level, dim_spectral], id_net), "def flux_net")
    call check(nf90_def_var(nc_out, "flux_down_direct", nf90_double, [dim_level, dim_spectral], id_direct), "def flux_direct")
    call check(nf90_put_att(nc_out, nf90_global, "repeats", nreps), "att repeats")
    call check(nf90_put_att(nc_out, nf90_global, "best_s", best), "att best")
    call check(nf90_put_att(nc_out, nf90_global, "mean_s", mean), "att mean")
    call check(nf90_put_att(nc_out, nf90_global, "std_s", std), "att std")
    call check(nf90_enddef(nc_out), "enddef output")
    call check(nf90_put_var(nc_out, id_up, up), "write flux_up")
    call check(nf90_put_var(nc_out, id_dn, dn), "write flux_down")
    call check(nf90_put_var(nc_out, id_net, net), "write flux_net")
    call check(nf90_put_var(nc_out, id_direct, direct), "write flux_direct")
    call check(nf90_close(nc_out), "close output")
  end subroutine write_output
end program rte_sw_py2sess
