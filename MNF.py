#!/usr/bin/python
# -*- coding: latin-1 -*-

########################################################################################################################
#
# MNF.py
# A python script to perform MNF transformation to remote sesning data.
#
# Info: The script perform MNF transformation to all raster images stored in a folder.
#
# Author: Javier Lopatin
# Email: javierlopatin@gmail.com
# Date: 09/08/2016
# Version: 1.0
#
# Usage:
#
# python MNF.py -i <Imput raster>
#               -c <Number of components [default = inputRaster bands]>
#               -p <Preprocessing: Brightness Normalization of Hyperspectral data [Optional]>
#               -s <Apply Savitzky Golay filtering [Optional]>
#
# # --preprop [-p]: Brightness Normalization presented in Feilhauer et al., 2010
#
# # examples:
#             # Get the regular MNF transformation
#             python MNF.py -i raster
#
#             # with Brightness Normalization
#             python MNF_cmd.py -i raster -p
#
#
#
# Bibliography:
#
# Feilhauer, H., Asner, G. P., Martin, R. E., Schmidtlein, S. (2010): Brightness-normalized Partial Least Squares
# Regression for hyperspectral data. Journal of Quantitative Spectroscopy and Radiative Transfer 111(12-13),
# pp. 1947–1957. 10.1016/j.jqsrt.2010.03.007
#
# C-I Change and Q Du. 1999. Interference and Noise-Adjusted Principal Components Analysis.
# IEEE TGRS, Vol 36, No 5.
#
########################################################################################################################

from __future__ import division
import argparse
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.base import BaseEstimator, TransformerMixin
try:
   import rasterio
except ImportError:
   print("ERROR: Could not import Rasterio Python library.")
   print("Check if Rasterio is installed.")

try:
   import pysptools.noise as ns
except ImportError:
   print("ERROR: Could not import Pysptools Python library.")
   print("Check if Pysptools is installed.")

################
### Functions
################


class MNF(BaseEstimator, TransformerMixin):
    """
    Apply a MNF transform to the image
    'img' must have (raw, column, band) shape
    """
    def __init__(self, n_components=1, BrightnessNormalization=False):
        self.n_components = n_components
        self.BrightnessNormalization = BrightnessNormalization
    def fit(self, X, y=None):
        return self  # nothing else to do
    def transform(self, X, y=None):
        X = X.astype('float32')
        # apply brightness normalization
        # if raster
        if self.BrightnessNormalization==True:
            def norm(r):
                    norm = r / np.sqrt( np.sum((r**2), 0) )
                    return norm
            if len(X.shape) == 3:
                X = np.apply_along_axis(norm, 2, X)
            # if 2D array
            if len(X.shape) == 2:
                    X = np.apply_along_axis(norm, 0, X)
        w = ns.Whiten()
        wdata = w.apply(X)
        numBands = X.shape[2]
        h, w, numBands = wdata.shape
        X = np.reshape(wdata, (w*h, numBands))
        pca = PCA()
        mnf = pca.fit_transform(X)
        mnf = np.reshape(mnf, (h, w, numBands))
        mnf = mnf[:,:,:self.n_components]
        var = np.cumsum(np.round(pca.explained_variance_ratio_, decimals=4)*100)
        return mnf, var

def saveMNF(img, inputRaster):
    # Save TIF image to a nre directory of name MNF
    img2 = np.transpose(img, [2,0,1]) # get to (band, raw, column) shape
    output = outMNF
    if args["preprop"]==True:
        output = output[:-4] + "_BN.tif"
    new_dataset = rasterio.open(output , 'w', driver='GTiff',
               height=inputRaster.shape[0], width=inputRaster.shape[1],
               count=img.shape[2], dtype=str(img.dtype),
               crs=inputRaster.crs, transform=inputRaster.transform)
    new_dataset.write(img2)
    new_dataset.close()

### Run process

if __name__ == "__main__":

    # create the arguments for the algorithm
    parser = argparse.ArgumentParser()

    parser.add_argument('-i','--inputRaster',
      help='Input raster', type=str, required=True)
    parser.add_argument('-c','--components',
      help='Number of components.', type=int, default=False)
    parser.add_argument('-p','--preprop',
      help='Preprocessing: Brightness Normalization of Hyperspectral data [Optional].',
      action="store_true", default=False)
    parser.add_argument('-s','--SavitzkyGolay',
      help='Apply Savitzky Golay filtering [Optional].',  action="store_true", default=False)

    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    args = vars(parser.parse_args())

    # data imputps/outputs
    inRaster = args["inputRaster"]
    outMNF = inRaster[:-4] + "_MNF.tif"

    # load raster
    with rasterio.open(inRaster) as r:
        r2 = r.read() # transform to array

    # set number of components to retrive
    if args["components"] is not None:
        n_components = args['components']
    else:
        n_components = r2.shape[0]

    img = np.transpose(r2, [1,2,0]) # get to (raw, column, band) shape
    
    #############
    ### Apply MNF
    # Apply Brightness Normalization if the option -p is added
    if args["preprop"]==True:
        print("Creating MNF components of " + inRaster)
        model = MNF(n_components=n_components, BrightnessNormalization=True)
        mnf, var = model.fit_transform(img)
        print("The accumulative explained variance per component is:")
        print(var)
    # otherwie
    else:
        print("Creating MNF components of " + inRaster)
        model = MNF(n_components=n_components)
        mnf, var = model.fit_transform(img)
        print("The accumulative explained variance per component is:")
        print(var)

    # save the MNF image and explained variance
    saveMNF(mnf, r)
    bandNames = []
    for i in range(mnf.shape[2]):
        a = "MNF" + str(i+1)
        bandNames.append(a)
    bandNames = pd.DataFrame(bandNames)
    variance = pd.DataFrame(var)
    txtOut = pd.concat([bandNames, variance], axis=1)
    txtOut.columns=["Bands", "AccVariance"]
    txtOut.to_csv(outMNF[:-4] + ".csv", index=False, header=True, na_rep='NA')
