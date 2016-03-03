import os

from twod_materials.utils import is_converged

from pymatgen.core.structure import Structure
from pymatgen.core.composition import Composition
from pymatgen.io.vasp.outputs import Vasprun

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import operator


def plot_ion_hull_and_voltages(ion='Li'):
    """
    Plots the phase diagram between the pure material and pure ion,
    Connecting the points on the convex hull of the phase diagram.
    """

    # Calculated with the relax_3d() function
    # in twod_materials.stability.startup
    ion_ev_fu = {'Li': -1.7540797}

    energy = Vasprun('vasprun.xml').final_energy
    composition = Structure.from_file('POSCAR').composition
    twod_material = composition.reduced_formula
    twod_ev_fu = energy / composition.get_reduced_composition_and_factor()[1]

    data = [(0, 0, 0, twod_ev_fu)]  # (at% ion, n_ions, E_F, abs_energy)
    for directory in [
            dir for dir in os.listdir(os.getcwd()) if os.path.isdir(dir)]:
        if is_converged(directory):
            os.chdir(directory)
            energy = Vasprun('vasprun.xml').final_energy
            composition = Structure.from_file('POSCAR').composition
            ion_fraction = composition.get_atomic_fraction(ion)

            no_ion_comp_dict = composition.as_dict()
            no_ion_comp_dict.update({ion: 0})
            no_ion_comp = Composition.from_dict(no_ion_comp_dict)

            n_twod_fu = no_ion_comp.get_reduced_composition_and_factor()[1]
            n_ions = composition[ion] / n_twod_fu

            E_F = (
                (energy - composition[ion] * ion_ev_fu[ion]
                 - twod_ev_fu * n_twod_fu)
                / composition.num_atoms
            )

            data.append((ion_fraction, n_ions, E_F, energy / n_twod_fu))

            os.chdir('../')
    data.append((1, 1, 0, ion_ev_fu[ion]))  # Pure ion

    sorted_data = sorted(data, key=operator.itemgetter(0))

    # Determine which compositions are on the convex hull.
    convex_points = [(0, 0, 0, twod_ev_fu)]
    concave_points = []
    voltage_profile = []
    j = 0
    k = 0
    for i in range(1, len(sorted_data) - 1):
        in_slope = (
            (sorted_data[i][2] - convex_points[j][2])
            / (sorted_data[i][0] - convex_points[j][0])
        )

        out_slope = (
            (sorted_data[i][2] - sorted_data[i + 1][2])
            / (sorted_data[i][0] - sorted_data[i + 1][0])
        )

        if out_slope >= in_slope:
            convex_points.append(sorted_data[i])
            voltage = -(
                ((sorted_data[i][3] - sorted_data[k][3])
                 - (sorted_data[i][1] - sorted_data[k][1]) * ion_ev_fu[ion])
                / (sorted_data[i][1] - sorted_data[k][1])
                )
            voltage_profile.append((sorted_data[k][0], voltage))
            voltage_profile.append((sorted_data[i][0], voltage))
            j += 1
            k = i
        else:
            concave_points.append(sorted_data[i])

    convex_points.append((1, 1, 0, ion_ev_fu[ion]))
    voltage_profile.append((voltage_profile[-1][0], 0))
    voltage_profile.append((1, 0))

    convex_ion_fractions = [tup[0] for tup in convex_points]
    convex_formation_energies = [tup[2] for tup in convex_points]
    concave_ion_fractions = [tup[0] for tup in concave_points]
    concave_formation_energies = [tup[2] for tup in concave_points]

    voltage_profile_x = [tup[0] for tup in voltage_profile]
    voltage_profile_y = [tup[1] for tup in voltage_profile]

    ax = plt.figure(figsize=(14, 10)).gca()

    ax.plot([0, 1], [0, 0], 'k--')
    ax.plot(convex_ion_fractions, convex_formation_energies, 'b-', marker='o',
            markersize=12, markeredgecolor='none')
    ax.plot(concave_ion_fractions, concave_formation_energies, 'r', marker='o',
            linewidth=0, markersize=12, markeredgecolor='none')

    ax2 = ax.twinx()
    ax2.plot(voltage_profile_x, voltage_profile_y, 'k-', marker='o')

    ax.text(0, 0.002, twod_material, family='serif', size=20)
    ax.text(0.99, 0.002, ion, family='serif', size=20,
            horizontalalignment='right')

    ax.set_xticklabels(ax.get_xticks(), family='serif', size=20)
    ax.set_yticklabels(ax.get_yticks(), family='serif', size=20)
    ax2.set_yticklabels(ax2.get_yticks(), family='serif', size=20)

    ax.set_xlabel(r'$\mathrm{at\/\%\/%s}$' % ion, size=28)
    ax.set_ylabel(r'$\mathrm{E_F\/(eV/atom)}$', size=28)

    ax2.yaxis.set_label_position("right")
    if ion == 'Li':
        ax2.set_ylabel(r'$\mathrm{Potential\/vs.\/Li/Li^+\/(V)}$', size=28)
    elif ion == 'Mg':
        ax2.set_ylabel(r'$\mathrm{Potential\/vs.\/Mg/Mg^{2+}\/(V)}$', size=28)
    elif ion == 'Al':
        ax2.set_ylabel(r'$\mathrm{Potential\/vs.\/Al/Al^{3+}\/(V)}$', size=28)

    plt.savefig('{}_hull.pdf'.format(ion), transparent=True)
