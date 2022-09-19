import numpy as np
import pandas as pd
import random


def ccn_model(eta_star, alpha, beta):
    return (1 - beta - alpha)*eta_star + alpha

def eta(x, environment):
    if environment=='sinusoid':
        return .5 + .5 * np.sin(2.9*x + .1)
    elif environment=='low_base_rate_sinusoid':
        return np.piecewise(x,[
            ((-1 <= x) & (x <= .28)),
            ((.28< x) & (x <= .71)),
            ((0.71 < x) & (x <= 1))],  
            [lambda v: .5+.5 *np.sin(.4*v -1.28), 
             lambda v: .5 + .5*np.sin(12*v-4.5),
             lambda v: .081+1.9*np.power((v-.7), 2) ])
    else: 
        return np.piecewise(x,[
            ((-1 <= x) & (x <= -.5)),
            ((-.5 < x) & (x <= 0.2069)),
            ((0.2069 < x) & (x <= 0.8)),
            ((0.8 < x) & (x <= 1))],  
            [lambda v: -1.5*v-.75, 
             lambda v: 1.4*v+.7,
             lambda v: -1.5*v+1.3,
             lambda v: 1.25*v - .9 ])
    

def pi(x, func):
    if func=='uniform': 
        return np.ones(x.shape)
        
    elif func=='linear': 
        return .2 * x + .4


def generate_syn_data(
    NS,
    y0_pdf='low_base_rate_sinusoid',
    y1_pdf='sinusoid',
    pi_pdf='linear',
    error_min=0.05,
    error_max=0.25
):
    
    alpha_0, alpha_1, beta_0, beta_1 = np.random.uniform(error_min, error_max, 4)

    # Define class probability functions
    x = np.linspace(-1, 1, num=NS)
    eta_star_0 = eta(x, environment=y0_pdf)
    eta_star_1 = eta(x, environment=y1_pdf)
    eta_y_0 = ccn_model(eta_star_0, alpha_0, beta_0)
    eta_y_1 = ccn_model(eta_star_1, alpha_1, beta_1)

    # Sample from target potential outcome class probability distributions
    YS_0 = np.random.binomial(1, eta_star_0, size=NS)
    YS_1 = np.random.binomial(1, eta_star_1, size=NS)

    # Apply measurement error model
    Y_0 = YS_0.copy()
    Y_0[(YS_0==0) & (np.random.binomial(1, alpha_0, size=NS)==1)] = 1
    Y_0[(YS_0==1) & (np.random.binomial(1, beta_0, size=NS)==1)] = 0

    Y_1 = YS_1.copy()
    Y_1[(YS_1==0) & (np.random.binomial(1, alpha_1, size=NS)==1)] = 1
    Y_1[(YS_1==1) & (np.random.binomial(1, beta_1, size=NS)==1)] = 0

    # Apply consistency to observe potential outcomes
    YS, Y = np.zeros(NS, dtype=np.int64), np.zeros(NS, dtype=np.int64)
    D = np.random.binomial(1, pi(x, func=pi_pdf), size=NS)

    YS[D==0] = YS_0[D==0]
    YS[D==1] = YS_1[D==1]

    Y[D==0] = Y_0[D==0]
    Y[D==1] = Y_1[D==1]

    expdf = pd.DataFrame({
        'X': x,
        'YS_0': YS_0,
        'YS_1': YS_1,
        'Y_0': Y_0,
        'Y_1': Y_1,
        'D': D,
        'YS': YS,
        'Y': Y
    })
    
    expdf = expdf.sample(frac=1).reset_index(drop=True)
    
    error_params = {
        'alpha_0': alpha_0,
        'alpha_1': alpha_1, 
        'beta_0': beta_0, 
        'beta_1': beta_1
    }
    
    return expdf, error_params