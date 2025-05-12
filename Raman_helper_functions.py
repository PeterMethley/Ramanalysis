# Ramanalysis: Helper functions for interactive comparison and matching of Raman spectra

# Copyright (C) 2025 , Peter Methley

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
from scipy.signal import find_peaks



def find_peak_positions(xx: np.ndarray, yy: np.ndarray, prominence_threshold=0.05, remove_bg=False):
    """Finds the peaks above a certain prominence threshold in a spectrum, returning their wavenumbers, heights and prominences

    Args:
        xx (np.ndarray): Array of wavenumbers
        yy (np.ndarray): Array of intensities
        prominence_threshold (float, optional): Prominence which all peaks must be above. Defaults to 0.05.
        remove_bg (bool, optional): Whether to remove background before peak finding. Disable if the background has already been subtracted; enable if not. Defaults to False.

    Returns:
        Tuple [ndarray, ndarray, ndarray]: Wavenumbers, heights, and prominences of the peaks.
    """    
    if remove_bg:
        with np.errstate(over="ignore"):
            background = arpls(yy)
            y_nobg = yy - background
    else:
        y_nobg = yy
    
    peaks, properties = find_peaks(y_nobg, prominence=prominence_threshold)
    
    x_peaks = xx[peaks]
    
    y_peaks = yy[peaks]
    
    return x_peaks, y_peaks, properties["prominences"]
    

def arpls(y: np.ndarray, lam=10000, ratio=0.05, itermax=100) -> np.ndarray:
    """Compute the baseline of a spectrum using the Asymmetrically Reweighted Penalized Least Squares method

    Args:
        y (np.ndarray): Input spectrum intensities
        lam (int, optional): Smoothing parameter. Defaults to 10000.
        ratio (float, optional): Convergence ratio. Defaults to 0.05.
        itermax (int, optional): Maximum number of iterations. Defaults to 100.

    Returns:
        np.ndarray: The baseline of the spectrum
    """   
    
    N = len(y)
    D = diags([1, -2, 1], [0, 1, 2], shape=(N - 2, N))
    H = lam * D.T.dot(D)
    w = np.ones(N)
    for i in range(itermax):
        W = diags(w, 0, shape=(N, N))
        WH = W + H
        z = spsolve(WH, w * y)
        d = y - z
        dn = d[d < 0]
        m = np.mean(dn)
        s = np.std(dn)
        wt = 1. / (1 + np.exp(2 * (d - (2 * s - m)) / s))
        if np.linalg.norm(w - wt) / np.linalg.norm(w) < ratio:
            break
        w = wt
    return z