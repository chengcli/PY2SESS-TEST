# py2sess vs RTE-RRTMGP Flux Comparison

Reference is RTE-RRTMGP RTE shortwave output on py2sess optical properties.
For net flux, py2sess `up - down` is compared against `-(RTE down - up)`.

| backend | quantity | max abs | max rel (%) | RMSE | sum abs diff |
|---|---:|---:|---:|---:|---:|
| native_cuda | flux_up | 3.906967e-03 | 7.081494e+01 | 3.265108e-03 | 1.003663e+05 |
| native_cuda | flux_down | 1.820074e-04 | 6.092159e-01 | 5.990646e-05 | 9.620458e+02 |
| native_cuda | flux_net_up_minus_down | 3.906967e-03 | 1.539453e+01 | 3.233606e-03 | 9.940429e+04 |
| numpy | flux_up | 3.924980e-03 | 7.081494e+01 | 3.264473e-03 | 1.003470e+05 |
| numpy | flux_down | 1.820074e-04 | 6.092159e-01 | 5.990646e-05 | 9.620458e+02 |
| numpy | flux_net_up_minus_down | 3.924980e-03 | 1.557904e+01 | 3.232965e-03 | 9.938498e+04 |
| torch_cuda | flux_up | 3.903824e-03 | 7.081494e+01 | 3.265109e-03 | 1.003663e+05 |
| torch_cuda | flux_down | 1.820074e-04 | 6.092159e-01 | 5.990646e-05 | 9.620458e+02 |
| torch_cuda | flux_net_up_minus_down | 3.903824e-03 | 1.551762e+01 | 3.233606e-03 | 9.940430e+04 |
| pyharp_disort_cpu | flux_up | 8.027594e-04 | 1.568992e+02 | 1.765728e-04 | 4.280886e+02 |
| pyharp_disort_cpu | flux_down | 1.484447e-04 | 1.000000e+02 | 4.763478e-05 | 6.826348e+02 |
| pyharp_disort_cpu | flux_net_up_minus_down | 7.964224e-04 | 1.153471e+02 | 1.807282e-04 | 2.545462e+02 |
| pyharp_toon_cpu | flux_up | 7.044478e-04 | 5.041002e+01 | 1.809271e-04 | 2.282730e+03 |
| pyharp_toon_cpu | flux_down | 8.975138e-05 | 6.120124e-01 | 2.926667e-05 | 4.705952e+02 |
| pyharp_toon_cpu | flux_net_up_minus_down | 6.937260e-04 | 1.752706e+00 | 1.784420e-04 | 1.812135e+03 |
| pyharp_toon_cuda | flux_up | 7.044478e-04 | 5.041002e+01 | 1.809271e-04 | 2.282730e+03 |
| pyharp_toon_cuda | flux_down | 8.975138e-05 | 6.120124e-01 | 2.926667e-05 | 4.705952e+02 |
| pyharp_toon_cuda | flux_net_up_minus_down | 6.937260e-04 | 1.752706e+00 | 1.784420e-04 | 1.812135e+03 |
