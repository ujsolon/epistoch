# -*- coding: utf-8 -*-
"""
Created on Sat Apr 25 11:55:02 2020

@author: Germán Riaño
"""
import numpy as np
from numpy import matlib as ml
from scipy.special import binom
from scipy.stats import expon, gamma, rv_continuous
from scipy import linalg

from pyphase.testing import assert_dist_identical, mix_rv

class PhaseTypeGen(rv_continuous):
    def __init__(self, alpha, A, prec=None):
        alpha = ml.mat(alpha)
        A = ml.mat(A)
        super(PhaseTypeGen, self).__init__(
            momtype=1,
            a=0,
            b=None,
            xtol=1e-14,
            badvalue=None,
            name="phase",
            longname=None,
            shapes=None,
            extradoc=None,
            seed=None,
        )
        self.alpha = alpha
        self.A = A
        self.alphaAi = None  # alpha * A^(-1), computed lazily
        self.erd = None  # Equilibrium residual distribution

    def _cdf(self, x):
        return np.asarray([1. - np.sum(self.alpha @ linalg.expm(self.A.A * xv) , axis=1) for xv in x])
    
    def _pdf(self, x):
        res = np.asarray([self.alpha @ linalg.expm(self.A.A * xv) @ self._get_a() for xv in x]).flatten()
        return res

    def _moments(self, k=None):
        if k is None:
            k=2
        moms = list()
        left = self.alpha
        for i in range(1, k+1):
            left = - i * self._solve_vector_A(left, self.A)
            moms.append(np.sum(left.flatten()))
        return moms
        
    def _stats(self):
        # Mean(‘m’), variance(‘v’), skew(‘s’), and/or kurtosis(‘k’).
        moments = self._moments(4)
        moments = np.concatenate(([1.0], moments))
        mean = moments[1]
        centered_moments = {
            n: sum([binom(n, k) * moments[k] * (-mean) ** (n - k) for k in range(0, n + 1)])
            for n in range(1, 5)
        }
        var = centered_moments[2]
        sd = np.sqrt(var)
        skew = centered_moments[3] / sd ** 3
        # kurtosis is fourth central moment / variance**2 - 3
        kurt = centered_moments[4] / (var * var) - 3.0
        return mean, var, skew, kurt

    def params(self):
        return self.alpha, self.A, self._get_a(), self.A.shape[0]

    def _get_a(self):
        return -np.sum(self.A, axis=1)

    def _solve_vector_A(self, vector, A):
        # Computes vector * A^(1), without actually inverting the matrix, by solving x * A = vector
        return np.linalg.solve(A.T, vector.T).T

    def _get_alpha_Ai(self):
        # Computes vector * A^(1), without actually inverting the matrix, by solving x * A = vector
        if self.alphaAi is None:
            self.alphaAi = self._solve_vector_A(self.alpha, self.A)
        return self.alphaAi

    def _get_erd(self):
        if self.erd is None:
            gamma = 1 / self.mean()
            self.erd = phase(-gamma * self._get_alpha_Ai(), self.A)
        return self.erd

    def loss1(self, x):
        # First order loss function
        return self.mean() * self._get_erd().sf(x)

    def equilibrium_pi(self):
        # Solution to pi (A + alpha * a)=0, pi * one = 1
        n = self.A.shape[0]
        a = self._get_a()
        matrix = self.A + a @ self.alpha + np.ones((n, n))
        return np.linalg.solve(matrix.T, np.ones(n).T).T

    def _pre_append(self, stg, pre):
        lines = stg.splitlines()
        result = [lines[0]]
        for line in lines[1:]:
            result.append(pre + line)
        return "\n".join(result)

    def __str__(self):
        options = {"precision": 2}
        alpha_stg = np.array2string(self.alpha, **options)
        A_stg = np.array2string(self.A, **options)
        return (
            "PhaseType: \n"
            f"  alpha = {alpha_stg}\n"
            f"  A     = {self._pre_append(A_stg,'          ')}"
        )

    def __repr__(self):
        return f"PH({self.alpha.__repr__()}, {self.A.__repr__()})"


phase = PhaseTypeGen


def ph_expon(lambd=None, mean=None):
    return ph_erlang(1, lambd, mean)


def ph_erlang(n, lambd=None, mean=None):
    """
    Builds an Erlang(n,lmbda).
    If mean is provided then lambda = n/mean

    Parameters
    ----------
    n : int
        The order of theis Erlang
    lambd : float, optional
        Provide only one between lambd or mean
    mean : float, optional
        Provide only one between lambd or mean

    Returns
    -------
    TYPE
        PH representation for an Erlang

    """
    if lambd is None and mean is None:
        raise ValueError('"You must provide one between mean and lambda')
    lambd = lambd if lambd is not None else n / mean
    A = -lambd * np.eye(n)
    for i in range(n - 1):
        A[i, i + 1] = lambd
    alpha = np.zeros(n)
    alpha[0] = 1
    return phase(alpha, A)


def _z(n1, n2):
    # quiclky generates zeros
    return np.zeros((n1, n2))


def ph_sum(ph1, ph2):
    alpha1, A1, a1, n1 = ph1.params()
    alpha2, A2, a2, n2 = ph2.params()
    alpha = np.block([alpha1, _z(1, n2)])
    A = np.block([[A1, a1 * alpha2], [_z(n2, n1), A2]])
    return phase(alpha, A)


def ph_mix(ph1, ph2, p1):
    alpha1, A1, a1, n1 = ph1.params()
    alpha2, A2, a2, n2 = ph2.params()
    alpha = np.block([p1 * alpha1, (1 - p1) * alpha2])
    A = np.block([[A1, _z(n1, n2)], [_z(n2, n1), A2]])
    return phase(alpha, A)


#######################################
#  T E S T I N G
#######################################


def test_ph_expo():
    lambd = 10
    exp = expon(scale=1.0 / lambd)
    dists = dict()
    dists["np"] = phase(alpha=np.array([1.0]), A=np.array([-lambd]))
    dists["float"] = phase(alpha=1.0, A=-lambd)
    dists["mat"] = phase(alpha=ml.mat([1.0]), A=ml.mat([[-lambd]]))
    dists["method"] = ph_expon(lambd)
    for name, dist in dists.items():
        assert_dist_identical(exp, dist, "Expo-" + name)


def test_ph_gamma():
    lam = 20.0
    n = 2
    gam = gamma(a=n, scale=1 / lam)
    a = [1.0, 0.0]
    A = [[-lam, lam], [0, -(lam)]]
    dists = dict()
    dists["np"] = phase(alpha=np.array(a), A=np.array(A))
    dists["mat"] = phase(alpha=ml.mat(a), A=ml.mat(A))
    dists["method"] = ph_erlang(2, lam)
    for name, dist in dists.items():
        assert_dist_identical(gam, dist, "Gamma-" + name)


def test_ph_sum():
    lam = 3.0
    v1 = phase(alpha=np.array([1.0]), A=np.array([-lam]))
    v2 = v1
    v = ph_sum(v1, v2)
    print(f"sum = {v}")
    expected = gamma(a=2, scale=1 / lam)
    assert_dist_identical(expected, v, "Sum Expos")


def test_ph_mix():
    lam1 = 4.0
    lam2 = 2.0
    p = 0.4
    v1 = ph_expon(lam1)
    v2 = ph_expon(lam2)
    v = ph_mix(v1, v2, p)
    print(f"mix = {v}")
    expected = mix_rv(ps=np.array([p, 1 - p]), vs=[v1, v2])
    x = np.array([1, 2, 3])
    print(f"v-cdf = {v.cdf(x)}")
    print(f"ex-cdf = {expected.cdf(x)}")
    print(f"v-moms: {[{n:v.moment(n) for n in range(1,4)}]}")
    print(f"exp-moms: {[{n:expected.moment(n) for n in range(1,4)}]}")
    assert_dist_identical(expected, v, "Mix-HyperExpo")


def test_loss1():
    lambd = 0.5
    v1 = ph_expon(lambd)
    x = np.linspace(1, 5, 1)
    exp_loss1 = lambda x: np.exp(-lambd * x) / lambd
    np.testing.assert_allclose(v1.loss1(x), exp_loss1(x))


def test_equilibrium_phases():
    v = ph_erlang(n=3, mean=3)
    print(v)
    pi = v.equilibrium_pi()
    print(pi)


if __name__ == "__main__":
    test_equilibrium_phases()
    test_ph_expo()
    test_ph_gamma()
    test_loss1()
    test_ph_sum()
    test_ph_mix()
