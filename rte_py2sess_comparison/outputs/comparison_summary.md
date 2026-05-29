# py2sess vs RTE-RRTMGP Flux Comparison

Reference is RTE-RRTMGP RTE shortwave output on py2sess optical properties.
For net flux, py2sess `up - down` is compared against `-(RTE down - up)`.

| backend | quantity | max abs | max rel (%) | RMSE | sum abs diff |
|---|---:|---:|---:|---:|---:|
| native_cpu | flux_up | 5.302756e-03 | 4.493597e+01 | 4.496571e-03 | 4.968820e+02 |
| native_cpu | flux_down | 7.016526e-04 | 5.819252e-01 | 1.317954e-04 | 7.032313e+00 |
| native_cpu | flux_net_up_minus_down | 5.302756e-03 | 8.448182e-01 | 4.437299e-03 | 4.898497e+02 |
| native_cuda | flux_up | 5.167051e-03 | 4.493597e+01 | 4.497775e-03 | 4.970145e+02 |
| native_cuda | flux_down | 7.016526e-04 | 5.819252e-01 | 1.317954e-04 | 7.032313e+00 |
| native_cuda | flux_net_up_minus_down | 5.167051e-03 | 8.240165e-01 | 4.438519e-03 | 4.899821e+02 |
| numpy | flux_up | 5.302756e-03 | 4.493597e+01 | 4.496685e-03 | 4.968943e+02 |
| numpy | flux_down | 7.016526e-04 | 5.819252e-01 | 1.317954e-04 | 7.032312e+00 |
| numpy | flux_net_up_minus_down | 5.302756e-03 | 8.448182e-01 | 4.437414e-03 | 4.898620e+02 |
| torch_cpu | flux_up | 5.302756e-03 | 4.493597e+01 | 4.496571e-03 | 4.968820e+02 |
| torch_cpu | flux_down | 7.016526e-04 | 5.819252e-01 | 1.317954e-04 | 7.032313e+00 |
| torch_cpu | flux_net_up_minus_down | 5.302756e-03 | 8.448182e-01 | 4.437299e-03 | 4.898496e+02 |
| torch_cuda | flux_up | 5.302756e-03 | 4.493597e+01 | 4.496571e-03 | 4.968820e+02 |
| torch_cuda | flux_down | 7.016526e-04 | 5.819252e-01 | 1.317954e-04 | 7.032313e+00 |
| torch_cuda | flux_net_up_minus_down | 5.302756e-03 | 8.448182e-01 | 4.437299e-03 | 4.898496e+02 |
| pyharp_disort_cpu | flux_up | 7.117887e-04 | 1.000000e+02 | 2.131256e-04 | 1.611473e+01 |
| pyharp_disort_cpu | flux_down | 1.246789e-03 | 1.000000e+02 | 1.586089e-04 | 1.930443e+00 |
| pyharp_disort_cpu | flux_net_up_minus_down | 1.481129e-03 | 1.000000e+02 | 2.769589e-04 | 1.804518e+01 |
| pyharp_toon_cpu | flux_up | 1.201192e-03 | 2.953772e+01 | 3.178154e-04 | 6.471705e+00 |
| pyharp_toon_cpu | flux_down | 6.811440e-04 | 5.908321e-01 | 9.334764e-05 | 4.372648e+00 |
| pyharp_toon_cpu | flux_net_up_minus_down | 1.201192e-03 | 5.908321e-01 | 3.203557e-04 | 2.099057e+00 |
| pyharp_toon_cuda | flux_up | 1.201192e-03 | 2.953772e+01 | 3.178154e-04 | 6.471705e+00 |
| pyharp_toon_cuda | flux_down | 6.811440e-04 | 5.908321e-01 | 9.334764e-05 | 4.372648e+00 |
| pyharp_toon_cuda | flux_net_up_minus_down | 1.201192e-03 | 5.908321e-01 | 3.203557e-04 | 2.099057e+00 |
