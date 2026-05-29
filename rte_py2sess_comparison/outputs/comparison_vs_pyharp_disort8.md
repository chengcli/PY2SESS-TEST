# Solver Accuracy vs pyharp DISORT 8-Stream

Reference: `pyharp_disort_cpu.npz`, generated with `--nstr 8`.

| solver | quantity | max abs | max rel (%) | RMSE | sum abs diff |
|---|---:|---:|---:|---:|---:|
| pydisort_disort_8stream_cpu | flux_up | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| pydisort_disort_8stream_cpu | flux_down | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| pydisort_disort_8stream_cpu | flux_net | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 | 0.000000e+00 |
| rte_rrtmgp_sw_gpu | flux_up | 7.117887e-04 | 5.844313e+03 | 2.131256e-04 | 1.611473e+01 |
| rte_rrtmgp_sw_gpu | flux_down | 1.246789e-03 | 5.010902e+06 | 1.586089e-04 | 1.930443e+00 |
| rte_rrtmgp_sw_gpu | flux_net | 1.481129e-03 | 5.009469e+06 | 2.769589e-04 | 1.804518e+01 |
| py2sess_native_cpu | flux_up | 5.528325e-03 | 6.190179e+03 | 4.649609e-03 | 5.129967e+02 |
| py2sess_native_cpu | flux_down | 1.846572e-03 | 5.026533e+06 | 2.206422e-04 | 5.101870e+00 |
| py2sess_native_cpu | flux_net | 5.528325e-03 | 5.024970e+06 | 4.624255e-03 | 5.078949e+02 |
| py2sess_native_cuda | flux_up | 5.385317e-03 | 6.190179e+03 | 4.650830e-03 | 5.131292e+02 |
| py2sess_native_cuda | flux_down | 1.846572e-03 | 5.026533e+06 | 2.206422e-04 | 5.101870e+00 |
| py2sess_native_cuda | flux_net | 5.385317e-03 | 5.024970e+06 | 4.625483e-03 | 5.080273e+02 |
| py2sess_numpy | flux_up | 5.528325e-03 | 6.190179e+03 | 4.649723e-03 | 5.130090e+02 |
| py2sess_numpy | flux_down | 1.846572e-03 | 5.026533e+06 | 2.206422e-04 | 5.101869e+00 |
| py2sess_numpy | flux_net | 5.528325e-03 | 5.024970e+06 | 4.624370e-03 | 5.079071e+02 |
| py2sess_torch_cpu | flux_up | 5.528325e-03 | 6.190179e+03 | 4.649608e-03 | 5.129967e+02 |
| py2sess_torch_cpu | flux_down | 1.846572e-03 | 5.026533e+06 | 2.206422e-04 | 5.101870e+00 |
| py2sess_torch_cpu | flux_net | 5.528325e-03 | 5.024970e+06 | 4.624255e-03 | 5.078948e+02 |
| py2sess_torch_cuda | flux_up | 5.528325e-03 | 6.190179e+03 | 4.649608e-03 | 5.129967e+02 |
| py2sess_torch_cuda | flux_down | 1.846572e-03 | 5.026533e+06 | 2.206422e-04 | 5.101870e+00 |
| py2sess_torch_cuda | flux_net | 5.528325e-03 | 5.024970e+06 | 4.624255e-03 | 5.078948e+02 |
| pyharp_toon_cpu | flux_up | 1.252781e-03 | 6.212468e+03 | 3.409521e-04 | 2.258644e+01 |
| pyharp_toon_cpu | flux_down | 1.790029e-03 | 5.027321e+06 | 2.091263e-04 | 2.442205e+00 |
| pyharp_toon_cpu | flux_net | 1.700528e-03 | 5.025757e+06 | 3.784546e-04 | 2.014423e+01 |
| pyharp_toon_cuda | flux_up | 1.252781e-03 | 6.212468e+03 | 3.409521e-04 | 2.258644e+01 |
| pyharp_toon_cuda | flux_down | 1.790029e-03 | 5.027321e+06 | 2.091263e-04 | 2.442205e+00 |
| pyharp_toon_cuda | flux_net | 1.700528e-03 | 5.025757e+06 | 3.784546e-04 | 2.014423e+01 |
