import random, torch
import numpy as np
import pandas as pd
import numpy.matlib
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.metrics import roc_auc_score
from numpy.random import permutation

from model import *

Y0_PDF = 'shalt_6cov_baseline'
Y1_PDF = 'shalt_6cov_intervention'
PI_PDF = '6cov_linear'

###########################################################
######## Error model functions
###########################################################

def pi(x, func):
    if func=='uniform': 
        return .5*np.ones(x.shape[0])
        
    elif func=='linear': 
        return .35 * x + .5

    elif func=='6cov_linear':
        return .6*x.mean(axis=1) +.1
    
    elif func=='6cov_linsep':
        return .4*(1-np.abs(x[:,0]-x[:,1])) + .3

def eta(x, environment):
    
    if environment=='shalt_6cov_baseline':
        return .8* (.25 *(1+np.sin(1.5*x[:,0]))*(1-np.cos(3.9*np.maximum(.85*x[:,2],.7*x[:,3])))) + .2 * (4*np.power((x[:,1]-.5), 2))

    elif environment=='shalt_6cov_intervention':
        return 1-np.power(x[:,0], 6)

    elif environment=='2D_linsep_intervention':
        y = np.zeros(x.shape[0])
        y[x[:,1] > (-x[:,0] + 1)] = 1
        return y

    elif environment=='2D_linsep_baseline':
        y = np.zeros(x.shape[0])
        y[x[:,1] > x[:,0]] = 1
        return y

    elif environment=='sinusoid':
        return .5 + .5 * np.sin(2.9*x + .1)

    elif environment=='piecewise_sinusoid':
        return np.piecewise(x,[
            ((-1 <= x) & (x <= -.61)),
            ((-.61 < x) & (x <= 0.921)),
            ((0.921 < x) & (x <= 1))],  
            [lambda v: .4+.4*np.cos(9*v+5.5), 
            lambda v: .5+.3*np.sin(8*v+.9)+.15*np.sin(10*v+.2)+.05*np.sin(30*v+.2),
            lambda v: np.power(v, 3)])

    elif environment=='low_base_rate_sinusoid':
        return .5-.5 * np.sin(2.9*x+.1)

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


def generate_syn_data_pdfviz(
    NS,
    eta0,
    eta1,
    pi_pdf=PI_PDF,
    alpha_0=0,
    alpha_1=0,
    beta_0=0,
    beta_1=0,
    shuffle=True
):

    K=1
    alpha_0_arr = alpha_0*np.ones(K)
    alpha_1_arr = alpha_1*np.ones(K)
    beta_0_arr = beta_0*np.ones(K)
    beta_1_arr = beta_1*np.ones(K)

    # Define class probability functions
    x = np.random.uniform(low=0, high=1, size=(NS, 6))
    eta_star_0 = eta0(x)
    eta_star_1 = eta1(x)

    # Sample from target potential outcome class probability distributions
    YS_0 = np.random.binomial(1, eta_star_0, size=NS)
    YS_1 = np.random.binomial(1, eta_star_1, size=NS)

    Y_0 = np.matlib.repmat(YS_0, K, 1).T
    Y_1 = np.matlib.repmat(YS_1, K, 1).T

    alpha_0_errors = np.array([np.random.binomial(1, alpha_0_arr[i], size=NS) for i in range(K)]).T
    alpha_1_errors = np.array([np.random.binomial(1, alpha_1_arr[i], size=NS) for i in range(K)]).T

    beta_0_errors = np.array([np.random.binomial(1, beta_0_arr[i], size=NS) for i in range(K)]).T
    beta_1_errors = np.array([np.random.binomial(1, beta_1_arr[i], size=NS) for i in range(K)]).T

    Y_0[alpha_0_errors == 1] = 1
    Y_0[beta_0_errors == 1] = 0

    Y_1[alpha_1_errors == 1] = 1
    Y_1[beta_1_errors == 1] = 0

    # Apply consistency assumption to observe potential outcomes
    YS = np.zeros(NS, dtype=np.int64)
    Y = np.zeros_like(Y_0)

    pD = pi(x, func=pi_pdf)
    D = np.random.binomial(1, pi(x, func=pi_pdf), size=NS)
    YS[D==0] = YS_0[D==0]
    YS[D==1] = YS_1[D==1]

    Y[D==0,:] = Y_0[D==0,:]
    Y[D==1,:] = Y_1[D==1,:]
        
    dataset_y = {
        'pYS_0': eta_star_0,
        'pYS_1': eta_star_1,
        'YS_0': YS_0,
        'YS_1': YS_1,
        'pD': pD,
        'D': D,
        'YS': YS
    }

    for yx in range(Y.shape[1]):
        dataset_y[f'Y{yx}'] = Y[:,yx]
        dataset_y[f'Y{yx}_0'] = Y_0[:,yx]
        dataset_y[f'Y{yx}_1'] = Y_1[:,yx]

    error_params = {
        'alpha_0': alpha_0_arr,
        'alpha_1': alpha_1_arr,
        'beta_0': beta_0_arr,
        'beta_1': beta_1_arr
    }

    X, Y = pd.DataFrame(x), pd.DataFrame(dataset_y)
   
    if shuffle: 
        suffle_ix = permutation(X.index)
        X = X.iloc[suffle_ix]
        Y = Y.iloc[suffle_ix]

    return X, Y, error_params

def generate_syn_data(
    NS,
    K=1,
    y0_pdf=Y0_PDF,
    y1_pdf=Y1_PDF,
    pi_pdf=PI_PDF,
    alpha_0=0,
    alpha_1=0,
    beta_0=0,
    beta_1=0,
    shuffle=True
):  

    alpha_0_arr = alpha_0*np.ones(K)
    alpha_1_arr = alpha_1*np.ones(K)
    beta_0_arr = beta_0*np.ones(K)
    beta_1_arr = beta_1*np.ones(K)

    # Define class probability functions
    x = np.random.uniform(low=0, high=1, size=(NS, 6))
    eta_star_0 = eta(x, environment=y0_pdf)
    eta_star_1 = eta(x, environment=y1_pdf)

    # Sample from target potential outcome class probability distributions
    YS_0 = np.random.binomial(1, eta_star_0, size=NS)
    YS_1 = np.random.binomial(1, eta_star_1, size=NS)

    Y_0 = np.matlib.repmat(YS_0, K, 1).T
    Y_1 = np.matlib.repmat(YS_1, K, 1).T

    alpha_0_errors = np.array([np.random.binomial(1, alpha_0_arr[i], size=NS) for i in range(K)]).T
    alpha_1_errors = np.array([np.random.binomial(1, alpha_1_arr[i], size=NS) for i in range(K)]).T

    beta_0_errors = np.array([np.random.binomial(1, beta_0_arr[i], size=NS) for i in range(K)]).T
    beta_1_errors = np.array([np.random.binomial(1, beta_1_arr[i], size=NS) for i in range(K)]).T

    Y_0[alpha_0_errors == 1] = 1
    Y_0[beta_0_errors == 1] = 0

    Y_1[alpha_1_errors == 1] = 1
    Y_1[beta_1_errors == 1] = 0

    # Apply consistency assumption to observe potential outcomes
    YS = np.zeros(NS, dtype=np.int64)
    Y = np.zeros_like(Y_0)

    pD = pi(x, func=pi_pdf)
    D = np.random.binomial(1, pi(x, func=pi_pdf), size=NS)
    YS[D==0] = YS_0[D==0]
    YS[D==1] = YS_1[D==1]

    Y[D==0,:] = Y_0[D==0,:]
    Y[D==1,:] = Y_1[D==1,:]
        
    dataset_y = {
        'pYS_0': eta_star_0,
        'pYS_1': eta_star_1,
        'YS_0': YS_0,
        'YS_1': YS_1,
        'pD': pD,
        'D': D,
        'YS': YS
    }

    for yx in range(Y.shape[1]):
        dataset_y[f'Y{yx}'] = Y[:,yx]
        dataset_y[f'Y{yx}_0'] = Y_0[:,yx]
        dataset_y[f'Y{yx}_1'] = Y_1[:,yx]

    error_params = {
        'alpha_0': alpha_0_arr,
        'alpha_1': alpha_1_arr,
        'beta_0': beta_0_arr,
        'beta_1': beta_1_arr
    }

    X, Y = pd.DataFrame(x), pd.DataFrame(dataset_y)
   
    if shuffle: 
        suffle_ix = permutation(X.index)
        X = X.iloc[suffle_ix]
        Y = Y.iloc[suffle_ix]

    return X, Y, error_params

def get_loaders(X, Y, target, do, conditional, split_frac=.7):

    split_ix = int(X.shape[0]*split_frac)
    
    X_train = X[:split_ix].to_numpy()
    Y_train = Y[:split_ix][target].to_numpy()[:, None]

    if conditional:
        X_train = X_train[Y[:split_ix]['D'] == do]
        Y_train = Y_train[Y[:split_ix]['D'] == do]

    X_val = X[split_ix:].to_numpy()
    Y_val = Y[split_ix:][f'YS_{do}'].to_numpy()[:, None]
    
    train_data = torch.utils.data.TensorDataset(torch.Tensor(X_train), torch.Tensor(Y_train))
    train_loader = torch.utils.data.DataLoader(train_data, batch_size=32, shuffle=True, num_workers=1)
    val_data = torch.utils.data.TensorDataset(torch.Tensor(X_val), torch.Tensor(Y_val))
    val_loader = torch.utils.data.DataLoader(val_data, batch_size=32, shuffle=False, num_workers=1)
    
    return train_loader, val_loader

###########################################################
######## Parameter estimation
###########################################################

def ccpe(X, Y, do, target, n_epochs):

    loss_config = {
        'alpha': None,
        'beta': None
    }
    
    train_loader, val_loader = get_loaders(X, Y, target, do, conditional=True)
    model = MLP()
    losses = train(model, 'Y|D', train_loader, loss_config=loss_config, n_epochs=n_epochs)
    x, y, py_hat = evaluate(model, val_loader)
    
    # Compute error parameters from predicted probabilities
    alpha_hat = py_hat.min()
    beta_hat = 1 - py_hat.max()

    debug_info = {
        'val_x': val_df['X'].to_numpy(),
        'val_py': py_hat
    }
    
    return alpha_hat, beta_hat, debug_info

###########################################################
######## Experiments
###########################################################


def run_baseline(X, Y, baseline, do, loss_config, n_epochs=5, train_ratio=.7):

    target = baseline['target']
    conditional = 'OBS' not in baseline['model']

    # Train model
    train_loader, val_loader = get_loaders(X, Y, target, do, conditional)
    model = MLP()
    losses = train(model, target, train_loader, loss_config=loss_config, n_epochs=n_epochs)
    
    # Evaluate on validation data
    x, y, py_hat = evaluate(model, val_loader)
    y_hat = np.zeros_like(y)
    y_hat[py_hat > .5] = 1
    auroc = roc_auc_score(y, py_hat)
    acc = (y_hat == y).mean()

    results = {}
    results['AU-ROC'] = auroc
    results['ACC'] = acc
    results['x'] = x
    results['y'] = y
    results['py_hat'] = py_hat

    return results

def run_baseline_comparison_exp(env, baselines, do,  N_RUNS, NS, K=1, n_epochs=5, alpha=0, beta=0):

    exp_results = {
        'model': [],
        'AU-ROC': [],
        'ACC': [],
        'alpha': [],
        'beta': []
    }
    
    for RUN in range(N_RUNS):
        print(f'=============== RUN: {RUN} ===============')

        X, Y, error_params = generate_syn_data(
            NS,
            K,
            y0_pdf=env['Y0_PDF'],
            y1_pdf=env['Y1_PDF'],
            pi_pdf=env['PI_PDF'],
            alpha_0=alpha,
            alpha_1=alpha,
            beta_0=beta,
            beta_1=beta,
            shuffle=True
        )

        for baseline in baselines:
            target = baseline['target']

            loss_config = {
                'alpha': error_params[f'alpha_{do}'][0] if 'SL' in baseline['model'] else None,
                'beta': error_params[f'beta_{do}'][0] if 'SL' in baseline['model'] else None,
                'prop_func': pi,
                'pi_pdf': env['PI_PDF'],
                'do': do,
                'pd': Y['D'].mean(),
                'reweight': True if 'RW' in baseline['model'] else False
            }

            results = run_baseline(X, Y, baseline, do, loss_config, n_epochs=n_epochs, train_ratio=.7)
            exp_results['model'].append(baseline['model'])
            exp_results['AU-ROC'].append(results['AU-ROC'])
            exp_results['ACC'].append(results['ACC'])
            exp_results['alpha'].append(error_params[f'alpha_{do}'][0])
            exp_results['beta'].append(error_params[f'beta_{do}'][0])
            
    return exp_results


def run_baseline_comparison_exp_grid(env, baselines, param_configs, do, N_RUNS, NS, K=1, n_epochs=5):

    exp_results = {
        'model': [],
        'AU-ROC': [],
        'ACC': [],
        'alpha': [],
        'beta': []
    }

    for config in param_configs:
    
        for RUN in range(N_RUNS):

            X, Y, error_params = generate_syn_data(
                NS,
                K,
                y0_pdf=env['Y0_PDF'],
                y1_pdf=env['Y1_PDF'],
                pi_pdf=env['PI_PDF'],
                alpha_0=config['alpha'],
                alpha_1=config['alpha'],
                beta_0=config['beta'],
                beta_1=config['beta'],
                shuffle=True
            )
      
            for baseline in baselines:
                print('======================================================================')
                print(f"RUN: {RUN}, model: {baseline['model']}, alpha: {config['alpha']}, beta: {config['beta']}")
                print('====================================================================== \n')
                target = baseline['target']
                loss_config = {
                    'alpha': config['alpha'] if 'SL' in baseline['model'] else None,
                    'beta': config['beta'] if 'SL' in baseline['model'] else None,
                    'prop_func': pi,
                    'pi_pdf': env['PI_PDF'],
                    'do': do,
                    'pd': Y['D'].mean(),
                    'reweight': True if 'RW' in baseline['model'] else False
                }
                print('error params', error_params)
                print('config alpha', config['alpha'])
                print('config beta', config['beta'])

                results = run_baseline(X, Y, baseline, do, loss_config, n_epochs=n_epochs, train_ratio=.7)
                exp_results['model'].append(baseline['model'])
                exp_results['AU-ROC'].append(results['AU-ROC'])
                exp_results['ACC'].append(results['ACC'])
                exp_results['alpha'].append(config['alpha'])
                exp_results['beta'].append(config['beta'])

    return exp_results

def run_estimation_error_exp(do, param_configs, error_param, NS, N_RUNS, n_epochs=5, train_ratio=.7):
    
    baseline = {
        'model': 'Conditional outcome (SL)',
        'target': 'Y0'
    }

    results = []
    for config in param_configs:
        surrogate = {}

        if error_param == 'alpha':
            alpha = config['param']
            surrogate['alpha'] = config['estimate']
            beta = 0
            surrogate['beta'] = 0

        if error_param == 'beta':
            beta = config['param']
            surrogate['beta'] = config['estimate']
            alpha = 0
            surrogate['alpha'] = 0
            
        for run in range(N_RUNS):

            X, Y, error_params = generate_syn_data(
                NS=NS,
                K=1,
                y0_pdf=Y0_PDF,
                y1_pdf=Y1_PDF,
                pi_pdf=PI_PDF,
                alpha_min=alpha,
                alpha_max=alpha+.001,
                beta_min=beta,
                beta_max=beta+.001,
                shuffle=True
            )

            run = run_baseline(X, Y, baseline, do=0,
                                    surrogate_params=surrogate, n_epochs=n_epochs, train_ratio=.7)
            result = {
                'AU-ROC': run['AU-ROC'],
                'ACC': run['ACC'],
                'alpha': alpha,
                'beta': beta, 
                'alpha_hat': surrogate['alpha'],
                'beta_hat': surrogate['beta'],
                'error_param': error_param
            }

            results.append(result)
        
    return results

def ccpe_benchmark_exp(SAMPLE_SIZES, N_RUNS, K, n_epochs):

    exp_results =  []
    py_results = {}

    for NS in SAMPLE_SIZES:
        py_results[NS] = {}
        for RUN in range(N_RUNS):
            py_results[NS][RUN] = {}

            X, Y, error_params = generate_syn_data(
                NS=NS,
                K=K,
                y0_pdf=Y0_PDF,
                y1_pdf=Y1_PDF,
                pi_pdf=PI_PDF,
                alpha_min=0.05,
                alpha_max=0.2499,
                beta_min=0.05,
                beta_max=0.2499
            )
            expdf = expdf.sample(frac=1).reset_index(drop=True)

            result = error_params.copy()
            result['NS'] = expdf.shape[0]
            result['alpha_hat'] = np.zeros((2, K))
            result['beta_hat'] = np.zeros((2, K))
            result['alpha_error'] = np.zeros((2, K))
            result['beta_error'] = np.zeros((2, K))

            for k in range(K):
                py_results[NS][RUN][k] = {}
                for d in [0]:
                    py_results[NS][RUN][k][d] = {}
                    alpha_hat, beta_hat, val_preds = ccpe(X, Y, target=f'Y{k}', do=d, n_epochs=n_epochs)
                    result['alpha_hat'][d][k] = alpha_hat
                    result['beta_hat'][d][k] = beta_hat

                    py_results[NS][RUN][k][d]['x'] = val_preds['val_x']
                    py_results[NS][RUN][k][d]['py'] = val_preds['val_py']
                    result['alpha_error'][d][k] = result['alpha_hat'][d][k] - error_params[f'alpha_{d}'][k]
                    result['beta_error'][d][k] = result['beta_hat'][d][k] - error_params[f'beta_{d}'][k]

            # Mean aggregation approach (not included in writeup)
            eta_0_bar = np.array([py_results[NS][RUN][k][0]['py'] for k in range(K)]).mean(axis=0).squeeze()
            alpha_0_bar_hat = eta_0_bar.min()
            beta_0_bar_hat = 1-eta_0_bar.max()

            py_results[NS][RUN]['eta_0_bar'] = eta_0_bar
            result['alpha_0_bar_hat'] = alpha_0_bar_hat
            result['beta_0_bar_hat'] = beta_0_bar_hat
            result['alpha_0_bar_error'] = alpha_0_bar_hat - error_params[f'alpha_0'].mean()
            result['beta_0_bar_error'] = beta_0_bar_hat - error_params[f'beta_0'].mean()

            exp_results.append(result)
    
    return exp_results, py_results

def get_ccpe_result_df(do, exp_results):
    full_exp_results = []
    for result in exp_results:
        for k in range(result['alpha_error'].shape[1]):
            
            full_exp_results.extend([{
                'NS': result['NS'],
                'parameter': 'alpha',
                'error': abs(result['alpha_error'][do][k]),
                'aggregate': False
            },{
                'NS': result['NS'],
                'parameter': 'beta',
                'error': abs(result['beta_error'][do][k]),
                'aggregate': False
            },{
                'NS': result['NS'],
                'parameter': 'alpha',
                'error': abs(result[f'alpha_{do}_bar_error']),
                'aggregate': True
            },{
                'NS': result['NS'],
                'parameter': 'beta',
                'error': abs(result[f'beta_{do}_bar_error']),
                'aggregate': True
            }])
            
                          
    return pd.DataFrame(full_exp_results)

