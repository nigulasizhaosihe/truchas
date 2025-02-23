!!
!! ALGEBRAIC_TURB_MODEL_TYPE
!!
!! This module provides an implementation of the abstract turbulence_model_class
!!
!! Peter Brady <ptb@lanl.gov>
!! May 2018
!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!
!! This file is part of Truchas. 3-Clause BSD license; see the LICENSE file.
!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!
!!  Calculates cell-centered turbulent diffusivity based on the
!!  algebraic turbulence model:
!!
!!  Nu_Turb = cmu * turbulence_length * turbulence_velocity
!!
!!   where turbulence_length is specified via input, and
!!   turbulence_velocity is determined from algebraic relations with the
!!   local velocities approximating the turbulence intensities.  No
!!   solution of transport equations is required.
!!
!!   Effective (Apparent) Diffusivity = Nu_Turb + Molecular Diffusivity
!!
!!   In the case of momentum transport, the diffusivity is also called
!!   kinematic viscosity (nu), which is given by mu / rho.
!!

module algebraic_turb_model_type

  use,intrinsic :: iso_fortran_env, only: r8 => real64
  use turbulence_model_class
  use parameter_list_type
  use truchas_logging_services
  use unstr_mesh_type
  use flow_props_type
  implicit none
  private

  public :: alloc_algebraic_turb_model

  type, extends(turbulence_model), public :: algebraic_turb_model
    real(r8) :: length
    real(r8) :: cmu
    real(r8) :: ke_fraction
    real(r8), allocatable :: nu_turb(:)
  contains
    procedure :: read_params
    procedure :: init
    procedure :: setup
    procedure :: apply
    procedure :: accept
  end type algebraic_turb_model

contains

  subroutine alloc_algebraic_turb_model(t)
    class(turbulence_model), allocatable, intent(out) :: t
    type(algebraic_turb_model), allocatable :: m
    allocate(m)
    call move_alloc(m, t)
  end subroutine alloc_algebraic_turb_model

  subroutine read_params(this, params)

    class(algebraic_turb_model), intent(inout) :: this
    type(parameter_list), pointer, intent(in) :: params

    call params%get('length', this%length)
    call params%get('cmu', this%cmu, default=0.05_r8)
    call params%get('ke fraction', this%ke_fraction, default=0.1_r8)

    if (this%length <= 0.0_r8) call TLS_fatal("turbulence length must be > 0")
    if (this%cmu <= 0.0_r8) call TLS_fatal("turbulence cmu must > 0")
    if (this%ke_fraction <= 0.0_r8 .or. this%ke_fraction >= 1.0_r8) &
        call TLS_fatal("turbulence ke fraction must be in (0,1)")

  end subroutine read_params

  subroutine init(this, mesh)
    class(algebraic_turb_model), intent(inout) :: this
    type(unstr_mesh), intent(in), target :: mesh
    this%mesh => mesh
    allocate(this%nu_turb(this%mesh%ncell))
  end subroutine init

  subroutine setup(this, vel_cc)
    class(algebraic_turb_model), intent(inout) :: this
    real(r8), intent(in) :: vel_cc(:,:)
    integer :: i
    associate(cmu => this%cmu, l => this%length, f => this%ke_fraction)
      do i = 1, this%mesh%ncell
        this%nu_turb(i) = cmu*l*sqrt(0.5_r8*f*sum(vel_cc(:,i)**2))
      end do
    end associate

  end subroutine setup

  subroutine apply(this, props)
    class(algebraic_turb_model), intent(inout) :: this
    type(flow_props), intent(inout) :: props
    integer :: i
    associate (rho => props%rho_cc, mu => props%mu_cc)
      do i = 1, this%mesh%ncell
        mu(i) = mu(i) + rho(i)*this%nu_turb(i)*this%mesh%volume(i)
      end do
    end associate
  end subroutine apply

  subroutine accept(this)
    class(algebraic_turb_model), intent(inout) :: this
  end subroutine accept

end module algebraic_turb_model_type
