# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:34:26 2020

@author: germanr
"""

import logging
import scipy
import numpy as np
import os

import matplotlib.pyplot as plt
from timeit import timeit


import epi_stoch.utils as utils
from epi_stoch.SIR_general import classicalSIR, stochasticSIR, print_error, report_summary
from epi_stoch.utils.plotting import plot_sir, plot_IR 


def performance_test(N):   
    tt=timeit(setup="from __main__ import classicalSIR",
              stmt="tc, Sc, Ic, Rc = classicalSIR(population=1000, use_odeint=True)",
              number=1000)
    print(f"tt odeint = {tt}")
    tt=timeit(setup="from __main__ import classicalSIR",
              stmt="tc, Sc, Ic, Rc = classicalSIR(population=1000, use_odeint=False)",
              number=1000)
    print(f"tt ivp = {tt}")
    tc, Sc, Ic, Rc = classicalSIR(population=N, use_odeint=True)
    tc2, Sc2, Ic2, Rc2 = classicalSIR(population=N, use_odeint=False)
    print(np.max(np.abs(Ic-Ic2))/N)
    print(np.max(np.abs(Sc-Sc2))/N)
    

def compare_models(name, dist, N=1000000, I0=1, num_days=100, R0=2.25):
    name1 = name + ":SIR"
    SIR_classic = classicalSIR(population=N,
                               I0=I0,
                               reproductive_factor=R0,
                               infectious_period_mean=dist.mean(), 
                               num_days=num_days)
    fig = plot_sir(name1, SIR_classic, N)    
    
    name2 = name + ":SIR-G"
    SIR_general = stochasticSIR(population=N, I0=I0,
                                num_days=num_days, 
                                delta=num_days/2000,
                                reproductive_factor=R0, 
                                disease_time_distribution=dist,
                                method='loss')
    plot_sir(name2, SIR_general, N, fig, linestyle='--')    
    plt.show()

    report_summary(name1, SIR_classic, N)
    report_summary(name2, SIR_general, N)
    print_error(SIR_classic, SIR_general, N)
    filename = os.path.join("../paper/epistoch/figures/", name + "-SIR-comp.pdf")
    print(f"Saving picture in file {os.path.abspath(filename)}")
    fig.savefig(filename, bbox_inches='tight')

    fig2 = plot_IR(name1, SIR_classic, N,)
    plot_IR(name2, SIR_general, N, fig2, linestyle='--')
    plt.show()    

    # save as PDF
    filename = os.path.join("../paper/epistoch/figures/", name + "-IR-comp.pdf")
    print(f"Saving picture in file {os.path.abspath(filename)}")
    fig2.savefig(filename, bbox_inches='tight')
    

def variance_analysis(N = 1000000, I0 = 1, num_days = 100, R0 = 2.25, infectious_period_mean = 4.4, cvs=[.5, 1., 2.]):

    dists = {}
    models = {}
    sir_classic =  classicalSIR(population=N,
                                I0=I0,
                                reproductive_factor=R0,
                                infectious_period_mean=infectious_period_mean,
                                num_days=num_days) 
    fig = plot_sir("SIR", sir_classic, N, formats={'I':'r-'})
    dist = utils.stats.constant(infectious_period_mean)
    sir_constant =   stochasticSIR(population=N, I0=I0,
                                             num_days=num_days, 
                                             delta=num_days/2000,
                                             reproductive_factor=R0, 
                                             disease_time_distribution=dist,
                                             method='loss')
    fig = plot_sir("Const", sir_constant, N, fig, formats={'I':'b-.'})

    dists['gamma'] =  utils.stats.get_gamma
    dists['lognorm'] = utils.stats.get_lognorm

    for cv in cvs:
        for dist_name, dist_getter in dists.items():
            infectious_period_sd = cv * infectious_period_mean
            dist= dist_getter(infectious_period_mean, infectious_period_sd)
            mod_name = f'{dist_name}-{cv:.2}'
            logging.info('Running {mod_name}')
            num_days = round(100 * max(1, cv))
            models[(dist,cv)] = stochasticSIR(population=N, I0=I0,
                                              num_days=num_days, 
                                              delta=num_days/2000,
                                              reproductive_factor=R0, 
                                              disease_time_distribution=dist,
                                              method='loss')
            models[(dist,cv)].name = mod_name
            plot_sir(mod_name,  models[(dist,cv)], N, fig, formats={'I':''}, linestyle='--')    
    plt.show()

    filename = os.path.join("../paper/epistoch/figures/", "Variance-Analysis.pdf")
    print(f"Saving picture in file {os.path.abspath(filename)}")
    fig.savefig(filename, bbox_inches='tight')
    
    return models


if __name__ == '__main__':
    # logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    # logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    logging.basicConfig()
    compare_models('DIVOC', scipy.stats.norm(loc=4.5, scale=1) )
    variance_analysis()