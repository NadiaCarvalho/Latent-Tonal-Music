"""
Implementation of circular statistics from BAMBI R package
"""
import numpy as np
import scipy.stats as stats

def rvmsin(n, alpha1, alpha2, kappa1, kappa2, rho):
    """
    This function generates random numbers from the bivariate von Mises sine distribution.
    n: sample size
    alpha1, alpha2, kappa1, kappa2, rho: parameters of the distribution
    """
    # Generate random deviates from a bivariate normal distribution with mean (0,0) and covariance matrix Sigma
    cov = np.array([[kappa1**2, kappa1*kappa2*rho], [kappa1*kappa2*rho, kappa2**2]])
    z = np.random.multivariate_normal(mean=[0,0], cov=cov, size=n)

    # Calculate the bivariate von Mises sine distribution
    x1 = alpha1 + np.sin(z[:,0])
    x2 = alpha2 + np.sin(z[:,1])

    return np.asarray([x1, x2]).T

def calc_corr_fl(x):
    """Fisher's linear correlation coefficient"""
    temp_1 = np.sin(x[:, 0, np.newaxis] - x[:, 0]
                    )  # calculate the difference in angles
    # calculate the difference in angles
    temp_2 = np.sin(x[:, 1, np.newaxis] - x[:, 1])
    # return the estimate of the correlation coefficient
    return np.sum(temp_1 * temp_2)/np.sqrt(np.sum(temp_1**2)*np.sum(temp_2**2))

def calc_corr_tau1(x):
    """Kendall's tau1"""
    N = x.shape[0]  # number of observations
    sum_delta_ij = 0  # initialize the sum of delta values
    for i in range(N-2):
        for j in range(i+1, N-1):
            sign_delta_ij = np.sign(x[i, :] - x[j, :])  # calculate the sign of delta_ij
            for k in range(j+1, N):
                sign_delta_jk = np.sign(x[j, :] - x[k, :])  # calculate the sign of delta_jk
                sign_delta_ki = np.sign(x[k, :] - x[i, :])  # calculate the sign of delta_ki
                sum_delta_ij += np.prod(sign_delta_ij) * np.prod(sign_delta_jk) * np.prod(sign_delta_ki)# update the sum
    return sum_delta_ij * 6.0 / (N*(N-1)*(N-2))  # return the estimate of tau1

def calc_corr_tau2(x):
    """Kendall's tau2"""
    N = x.shape[0]  # number of observations
    num = 0  # initialize the sum of delta values
    for i in range(0, N-1):  # loop over all pairs of observations
        for j in range(i+1, N):  # loop over all pairs of observations
            # calculate the difference in angles
            theta_ij, phi_ij = x[i] - x[j]
            num += np.sign(theta_ij * phi_ij) * np.sign(abs(theta_ij) -
                                                        np.pi) * np.sign(abs(phi_ij) - np.pi)  # update the sum
    return 2 * num/(N * (N-1))  # return the estimate of tau2


def prncp_reg(x):
    """makes a single angle in [0, 2*pi]"""
    return (x + 2 * np.pi) % (2 * np.pi)  # return the principal angle


"""
Circular statistics
"""


def circ_cor(x, type="js", alternative="two.sided", jackknife=False, bootse=False, n_boot=100):
    """
    Sample circular correlation coefficients
    ----------
    Python implementation of the circ_cor function from the BAMBI R package.
    at https://rdrr.io/github/c7rishi/BAMBI/man/circ_cor.html
    ----------

    Parameters
    ----------
    - @param x: a 2D array of circular data, Nan values are not allowed.
    - @param type: type of correlation coefficient,
        - Possible Values:
            - "js" for Jammalamadaka-Sarma form (default) [parametric]
            - "fl" for Fisher-Lee's linear correlation coefficient [parametric]
            - "tau1" for Kendall's tau1 [non-parametric]
            - "tau2" for Kendall's tau2 [non-parametric]
    - @param alternative: alternative hypothesis, performed only when type is either "fl" or "js",
    in which case asymptotic standard error of the estimator is used to construct the test statistic.
        - Possible Values:
            - "two_sided" for two-sided test (default)
            - "less" for one-sided test, H0: rho >= 0
            - "greater" for one-sided test, H0: rho <= 0
    - @param jackknife: if True, jackknife estimate and standard error are returned
    - @param bootse: if True, bootstrap standard error is returned
    - @param n_boot: number of bootstrap samples (default 100), only used if bootse is True

    Returns
    ----------
    - @return: a dictionary containing the following keys:
        - "val": the estimate of the correlation coefficient
        - "se": the standard error of the estimate
        - "jackknife.est": the jackknife estimate of the correlation coefficient (only if jackknife is True)
        - "jackknife.se": the jackknife standard error of the correlation coefficient (only if jackknife is True)
        - "bootse": the bootstrap standard error of the correlation coefficient (only if bootse is True)
        - "pval": the p-value of the test (only if type is either "fl" or "js")

    Details
    -------
    circ_cor calculates the (sample) circular correlation between the columns of x.
    Two parametric (the Jammalamadaka-Sarma (1988, equation 2.6) form "js", and the Fisher-Lee (1983, Section 3) form "fl")
    and two non-parametric (two versions of Kendall's tau) correlation coefficients are considered.
    The first version of Kendall's tau ("tau1") is based on equation 2.1 in Fisher and Lee (1982),
    whereas the second version ("tau2") is computed using equations 6.7-6.8 in Zhan et al (2017).

    The cost-complexity for "js", "fl", "tau2" and "tau1" are O(n), O(n^2), O(n^2) and O(n^3) respectively,
    where n denotes the number of rows in x. As such, for large n evaluation of "tau1" will be slow.

    References
    ----------
    - Fisher, N. I. and Lee, A. J. (1982). Nonparametric measures of angular-angular association. Biometrika, 69(2), 315-321.
    - Fisher, N. I. and Lee, A. J. (1983). A correlation coefficient for circular data. Biometrika, 70(2):327-332.
    - Jammalamadaka, S. R. and Sarma, Y. (1988). A correlation coefficient for angular variables. Statistical theory and data analysis II, pages 349-364.
    - Zhan, X., Ma, T., Liu, S., & Shimizu, K. (2017). On circular correlation for data on the torus. Statistical Papers, 1-21.

    Examples
    --------
    - generate data from vmsin model \\
        ``np.random.seed(1)`` \\
        ``dat = rvmsin(100, 2, 3, -0.8, 0,0)``

    - now calculate circular correlation(s) between the 2 columns of data \\
        ``circ_cor(dat, type="js")`` \\
        ``circ_cor(dat, type="fl")`` \\
        ``circ_cor(dat, type="tau1")`` \\
        ``circ_cor(dat, type="tau2")``
    """
    if any(x0 for x0 in x.flatten() if np.isnan(x0)):
        raise ValueError("Nan values are not allowed.")

    if x.ndim != 2:
        raise ValueError("Input array must be 2D.")

    x = prncp_reg(x)
    n = x.shape[0]

    if type == 'fl':
        def calc_rho(x):  # type: ignore
            rho = calc_corr_fl(x)

            def a_over_mu2(margin):
                """A function to calculate a/mu^2"""
                alpha = np.array(
                    list(map(lambda p: np.sum(np.cos(p*margin))/n, [1, 2])))
                beta = np.array(
                    list(map(lambda p: np.sum(np.sin(p*margin))/n, [1, 2])))
                a_val = alpha[0]**2 + beta[0]**2 + alpha[1] * beta[0]**2 - \
                    alpha[0]**2 * alpha[1] - 2*alpha[1]*beta[0]*beta[1]
                mu_2 = 0.5 * (1 - alpha[1]**2 - beta[1]**2)
                return a_val / mu_2

            avar = np.prod(np.apply_along_axis(a_over_mu2, 0, x))
            se = np.sqrt(avar)/np.sqrt(n)
            return {'val': rho, 'se': se}
    elif type == 'js':
        def calc_rho(x):  # type: ignore
            sin_x_1_cent = np.sin(
                x[:, 0] - np.arctan2(np.sum(np.sin(x[:, 0])), np.sum(np.cos(x[:, 0]))))
            sin_x_2_cent = np.sin(
                x[:, 1] - np.arctan2(np.sum(np.sin(x[:, 1])),  np.sum(np.cos(x[:, 1]))))
            num = np.sum(sin_x_1_cent*sin_x_2_cent)
            den = np.sqrt(np.sum(sin_x_1_cent**2)*np.sum(sin_x_2_cent**2))
            rho = num/den

            idx = np.asarray(
                [[2, 2], [2, 0], [0, 2], [1, 3], [3, 1], [4, 0], [0, 4]])
            rownames = [''.join([str(i) for i in id]) for id in idx]
            lambda_x = np.apply_along_axis(lambda ii: np.sum(
                sin_x_1_cent**ii[0] * sin_x_2_cent**ii[1])/n, 1, idx)
            avar = max(
                lambda_x[rownames.index('22')] / lambda_x[rownames.index('20')] * lambda_x[rownames.index('02')] -
                rho * (
                    lambda_x[rownames.index('13')] / (lambda_x[rownames.index('20')] * np.sqrt(lambda_x[rownames.index('20')] * lambda_x[rownames.index('02')])) +
                    lambda_x[rownames.index('31')] / (lambda_x[rownames.index('02')] * np.sqrt(
                        lambda_x[rownames.index('20')] * lambda_x[rownames.index('02')]))
                ) +
                rho**2 / 4 * (
                    1 +
                    lambda_x[rownames.index('40')] / lambda_x[rownames.index('20')]**2 +
                    lambda_x[rownames.index('04')] / lambda_x[rownames.index('02')]**2 +
                    lambda_x[rownames.index(
                        '22')] / (lambda_x[rownames.index('20')] * lambda_x[rownames.index('02')])
                ),
                1e-10
            )

            se = np.sqrt(avar)/np.sqrt(n)
            return {'val': rho, 'se': se}
    elif type == 'tau1':
        def calc_rho(x):  # type: ignore
            return { 'val': calc_corr_tau1(x) }
    elif type == 'tau2':
        def calc_rho(x):  # type: ignore
            return { 'val': calc_corr_tau2(x) }
    else:
        ValueError("type must be one of 'js', 'fl', 'tau1', 'tau2'.")
        return

    rho = calc_rho(x)

    if jackknife:
        vals_adj = n*rho['val'] - (n-1)*np.asarray([calc_rho(x[np.arange(n) != ii, :])['val']
                              for ii in range(n)])
        rho['jackknife.est'] = np.sum(vals_adj)/n
        rho['jackknife.se'] = np.std(vals_adj)

    if bootse:
        rho['bootse'] = np.std(np.asarray([calc_rho(
            x[np.random.choice(n, n, replace=True), :])['val'] for _ in range(n_boot)]))

    if type in ["js", "fl"]:
        z = np.array(rho['val']) / rho['se']
        if alternative == "two.sided":
            rho['pval'] = 2 * stats.norm.sf(np.abs(z))
        elif alternative == "less":
            rho['pval'] = stats.norm.cdf(z)
        elif alternative == "greater":
            rho['pval'] = stats.norm.sf(z)

    return rho


if __name__ == "__main__":
    x = np.asarray([[0.444089551, 0.624964316],
                    [0.633804544, 5.826410858],
                    [0.825714435, 6.167345112],
                    [1.108044213, 5.110964151],
                    [6.095708748, 6.217210815],
                    [0.516724327, 5.569784597],
                    [5.525642365, 5.879254828],
                    [5.921935594, 0.777378087],
                    [6.014578437, 6.244945079],
                    [0.736373925, 0.271548330],
                    [5.116094635, 5.835679419],
                    [0.670091155, 5.873271030],
                    [0.542838152, 0.268022583],
                    [0.286759607, 1.116281710],
                    [0.216385118, 6.100955000],
                    [5.813978868, 5.760798310],
                    [5.807965155, 0.845173453],
                    [0.319097349, 6.159813587],
                    [0.413445934, 0.540051824],
                    [0.234442456, 0.060141342],
                    [0.376364314, 0.930890788],
                    [4.365264029, 0.418309642],
                    [6.100228795, 6.187808227],
                    [0.417788191, 0.152376593],
                    [1.003957650, 6.213024703],
                    [0.035987213, 5.149710122],
                    [5.548032146, 0.959238603],
                    [5.694862201, 5.535752548],
                    [0.653604778, 5.266077511],
                    [5.927714081, 6.140824245],
                    [0.116530517, 0.229582042],
                    [4.742404968, 0.414480561],
                    [4.473586667, 5.835213604],
                    [1.042247005, 0.464728914],
                    [1.095655847, 5.537592723],
                    [0.045846963, 5.962154971],
                    [0.316100912, 0.820720601],
                    [2.334370776, 5.063716770],
                    [4.504546721, 0.077780619],
                    [1.047761050, 5.460982689],
                    [5.540128600, 6.042945750],
                    [0.457901940, 5.493443914],
                    [0.444488712, 5.655617911],
                    [0.598123874, 5.413057085],
                    [0.882845234, 0.692967978],
                    [0.485179133, 0.870463445],
                    [0.048183207, 5.874256666],
                    [4.946216597, 0.561471195],
                    [5.543669398, 6.203606784],
                    [5.597128021, 1.022087640],
                    [0.949840349, 1.114829498],
                    [5.265551305, 6.273575082],
                    [6.043441634, 6.205446218],
                    [1.455216370, 5.968524702],
                    [6.219508897, 6.064201496],
                    [5.969860955, 0.078869744],
                    [1.061320734, 0.230798952],
                    [5.731491364, 0.008566996],
                    [4.589052449, 0.461154053],
                    [5.617495236, 5.075879506],
                    [2.178082723, 5.290985159],
                    [1.348006664, 5.741166196],
                    [5.609240918, 5.380346425],
                    [1.388808115, 0.042214836],
                    [5.710740528, 5.896786838],
                    [1.798827221, 5.865732503],
                    [0.004123956, 5.443678617],
                    [0.601550536, 4.883545280],
                    [6.163492484, 6.063065069],
                    [5.594540705, 5.582271034],
                    [5.115624542, 6.168083014],
                    [5.718811153, 0.207164189],
                    [5.505686814, 1.147686111],
                    [5.463711523, 0.327282227],
                    [3.595606722, 0.231885638],
                    [0.475979481, 5.890799085],
                    [5.422729677, 5.450274850],
                    [0.108422418, 5.873648956],
                    [0.446702997, 0.238248771],
                    [5.409901686, 6.191464263],
                    [0.392624104, 6.267717449],
                    [0.700084478, 4.875082525],
                    [4.591399789, 5.860210794],
                    [0.021587072, 6.113344989],
                    [6.197198439, 1.977237147],
                    [5.208614313, 0.102073317],
                    [0.069062661, 6.017951907],
                    [0.069547049, 0.261186864],
                    [5.964477112, 5.632519343],
                    [0.329671042, 0.229759354],
                    [6.156282119, 0.290873647],
                    [5.284744308, 6.141890119],
                    [0.159388443, 0.531137180],
                    [5.142554436, 0.251053118],
                    [0.108609983, 0.427331144],
                    [1.630796547, 4.984768745],
                    [0.217259424, 0.179661533],
                    [4.978988039, 5.953399342],
                    [0.876627830, 6.134928796],
                    [5.771628749, 6.012287533]])

    print(rvmsin(100, 2, 3, -0.8, 0,0))

    rho = circ_cor(x, "tau2")
    print(rho)
