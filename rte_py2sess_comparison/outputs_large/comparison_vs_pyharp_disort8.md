# Solver Accuracy vs pyharp DISORT 8-Stream

Reference: `pyharp_disort_cpu.npz`, generated with `--nstr 8`.

| solver | quantity | max abs | max rel (%) | RMSE | sum abs diff |
|---|---:|---:|---:|---:|---:|
| pydisort_disort_8stream_cpu | flux_up | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| pydisort_disort_8stream_cpu | flux_down | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| pydisort_disort_8stream_cpu | flux_net | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| rte_rrtmgp_sw_gpu | flux_up | 8.027594e-04 | 7.788695e+05 | 1.765728e-04 | 4.280886e+02 |
| rte_rrtmgp_sw_gpu | flux_down | 1.484447e-04 | 1.395594e+06 | 4.763478e-05 | 6.826348e+02 |
| rte_rrtmgp_sw_gpu | flux_net | 7.964224e-04 | 1.160603e+06 | 1.807282e-04 | 2.545462e+02 |
| py2sess_native_cuda | flux_up | 3.986356e-03 | 9.029686e+05 | 3.286123e-03 | 9.993825e+04 |
| py2sess_native_cuda | flux_down | 2.217284e-04 | 1.400996e+06 | 2.654977e-05 | 2.794110e+02 |
| py2sess_native_cuda | flux_net | 3.986356e-03 | 1.148142e+06 | 3.278627e-03 | 9.965884e+04 |
| py2sess_numpy | flux_up | 4.003093e-03 | 9.029686e+05 | 3.285478e-03 | 9.991894e+04 |
| py2sess_numpy | flux_down | 2.217284e-04 | 1.400996e+06 | 2.654977e-05 | 2.794110e+02 |
| py2sess_numpy | flux_net | 4.003093e-03 | 1.148142e+06 | 3.277981e-03 | 9.963952e+04 |
| py2sess_torch_cuda | flux_up | 3.981921e-03 | 9.029686e+05 | 3.286123e-03 | 9.993826e+04 |
| py2sess_torch_cuda | flux_down | 2.217284e-04 | 1.400996e+06 | 2.654977e-05 | 2.794110e+02 |
| py2sess_torch_cuda | flux_net | 3.981921e-03 | 1.148142e+06 | 3.278627e-03 | 9.965885e+04 |
| pyharp_toon_cpu | flux_up | 2.972495e-04 | 7.821054e+05 | 1.011729e-04 | 1.854641e+03 |
| pyharp_toon_cpu | flux_down | 1.746556e-04 | 1.401207e+06 | 2.698480e-05 | 2.120396e+02 |
| pyharp_toon_cpu | flux_net | 2.972495e-04 | 1.155982e+06 | 1.022342e-04 | 2.066681e+03 |
| pyharp_toon_cuda | flux_up | 2.972495e-04 | 7.821054e+05 | 1.011729e-04 | 1.854641e+03 |
| pyharp_toon_cuda | flux_down | 1.746556e-04 | 1.401207e+06 | 2.698480e-05 | 2.120396e+02 |
| pyharp_toon_cuda | flux_net | 2.972495e-04 | 1.155982e+06 | 1.022342e-04 | 2.066681e+03 |
