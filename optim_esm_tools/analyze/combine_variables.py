import string
import typing as ty
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

import optim_esm_tools as oet
from optim_esm_tools.analyze.time_statistics import default_thresholds


class VariableMerger:
    """The `VariableMerger` class is used to merge and process variables from
    multiple datasets, applying masks and generating visualizations."""

    full_paths = None
    source_files: ty.Mapping
    common_mask: xr.DataArray

    def __init__(
        self,
        data_set: ty.Optional[xr.Dataset] = None,
        paths: ty.Optional[ty.Iterable[str]] = None,
        other_paths: ty.Optional[ty.Iterable[str]] = None,
        merge_method: str = 'logical_or',
        tipping_thresholds: ty.Optional[ty.Mapping] = None,
        table_formats: ty.Optional[ty.Dict[str, str]] = None,
    ) -> None:
        if data_set is None:
            assert paths, "Dataset specified, don't give paths"
        else:
            assert not paths, 'Dataset not specified, give paths!'  # pragma: no cover
        self.data_set = data_set

        self.mask_paths = paths
        self.other_paths = other_paths or []

        self.merge_method = merge_method
        self.tipping_thresholds = tipping_thresholds
        self.table_formats = table_formats
        if data_set:
            return  # pragma: no cover
        source_files, common_mask = self.process_masks()
        self.source_files = source_files
        self.common_mask = common_mask

    def squash_sources(self) -> xr.Dataset:
        if self.data_set:
            return self.data_set  # pragma: no cover
        new_ds = self._squash_variables()
        new_ds = self._merge_squash(new_ds)
        return new_ds

    def _squash_variables(self) -> ty.Mapping:
        common_mask = (
            self.common_mask
            if self.common_mask.dims == ('lat', 'lon')
            else oet.analyze.xarray_tools.reverse_name_mask_coords(self.common_mask)
        )

        new_ds = defaultdict(dict)
        new_ds['data_vars']['global_mask'] = common_mask
        for var, path in self.source_files.items():
            _ds = oet.load_glob(path)
            for sub_variable in list(_ds.data_vars):
                if var not in sub_variable:
                    continue

                new_ds['data_vars'][sub_variable] = (
                    _ds[sub_variable]
                    .where(common_mask)
                    .mean(oet.config.config['analyze']['lon_lat_dim'].split(','))
                )
                new_ds['data_vars'][sub_variable].attrs = _ds[sub_variable].attrs

        # Make one copy - just use the last dataset
        new_ds['data_vars']['cell_area'] = _ds['cell_area']  # type: ignore
        keys = sorted(list(self.source_files.keys()))
        new_ds['attrs'] = dict(
            variables=keys,
            source_files=[self.source_files[k] for k in keys],
            mask_files=sorted(self.mask_paths),  # type: ignore
            paths=self.mask_paths,
            other_paths=self.other_paths,
        )
        return new_ds

    @staticmethod
    def _merge_squash(new_ds) -> xr.Dataset:
        try:
            new_ds = xr.Dataset(**new_ds)
        except TypeError as e:  # pragma: no cover
            oet.get_logger().warning(f'Ran into {e} fallback method because of cftime')
            # Stupid cftime can't compare it's own formats
            # But xarray can fudge something along the way!
            data_vars = new_ds.pop('data_vars')
            new_ds = xr.Dataset(**new_ds)

            for k, v in data_vars.items():
                if 'time' in new_ds.coords and 'time' in v.coords:
                    new_ds[k] = ('time', v.values)
                    new_ds[k].attrs = v.attrs
                else:
                    new_ds[k] = v
        return new_ds

    def make_fig(self, ds=None, fig_kw=None, add_histograms=False):
        ds = ds or self.squash_sources()

        return self._make_fig(ds, fig_kw=fig_kw, add_histograms=add_histograms)

    @staticmethod
    def _guess_fig_kw(keys, add_histograms=False):
        if add_histograms:
            return dict(
                mosaic=''.join(f'{k}.\n' for k in keys),
                figsize=(17, 5 * ((2 + len(keys)) / 3)),
                gridspec_kw=dict(width_ratios=[1, 0.5, 1.5], wspace=0.1, hspace=0.4),
            )
        return dict(
            mosaic=''.join(f'{k}.\n' for k in keys),
            figsize=(17, 4 * ((2 + len(keys)) / 3)),
            gridspec_kw=dict(width_ratios=[1, 1], wspace=0.1, hspace=0.05),
        )

    def _make_fig(
        self,
        ds: xr.Dataset,
        fig_kw: ty.Optional[ty.Mapping] = None,
        add_histograms: bool = False,
    ):
        variables = list(oet.utils.to_str_tuple(ds.attrs['variables']))
        mapping = {string.ascii_lowercase[i]: v for i, v in enumerate(variables)}
        keys = (
            [f'{k}{k.upper()}' for k in mapping] + ['tt']
            if add_histograms
            else list(mapping) + ['t']
        )
        fig_kw = fig_kw or self._guess_fig_kw(keys, add_histograms)

        _, axes = plt.subplot_mosaic(**fig_kw)

        if len(var_keys := list(mapping.keys())) > 1:
            for k in var_keys[1:]:
                axes[k].sharex(axes[var_keys[0]])  # type: ignore

        for key, var in mapping.items():
            plt.sca(axes[key])  # type: ignore
            plot_kw = dict(label=var)
            rm_kw = {
                k: v
                for k, v in {
                    **plot_kw,
                    **dict(alpha=0.5, add_label=False, set_y_lim=False),
                }.items()
                if k != 'label'
            }
            var_rm = (
                var
                + '_run_mean_'
                + oet.config.config['analyze']['moving_average_years']
            )
            oet.plotting.map_maker.plot_simple(ds, var_rm, **rm_kw)
            oet.plotting.map_maker.plot_simple(ds, var, **plot_kw)  # type: ignore
            plt.legend(loc='center left')
            if add_histograms:
                plt.sca(axes[key.upper()])  # type: ignore
                hist_kw = dict(bins=25, range=[np.nanmin(ds[var]), np.nanmax(ds[var])])
                self.simple_hist(ds, var, hist_kw=hist_kw)
                self.simple_hist(ds, var_rm, hist_kw=hist_kw, add_label=False)
        ax = plt.gcf().add_subplot(
            1,
            2,
            2,
            projection=oet.plotting.plot.get_cartopy_projection(),
        )
        oet.plotting.map_maker.overlay_area_mask(
            ds.where(ds['global_mask']).copy(),
            ax=ax,
        )
        summary = self.summarize_stats(ds)
        res_f, tips = result_table(
            summary,
            thresholds=self.tipping_thresholds,
            formats=self.table_formats,
        )
        self.add_table(
            res_f=res_f,
            tips=tips,
            ax=axes['t'],  # type: ignore
            ha='center' if add_histograms else 'bottom',
        )
        axes['global_map'] = ax  # type: ignore
        return axes

    @staticmethod
    def simple_hist(ds, var, hist_kw=None, add_label=True, **plot_kw):
        da = ds[var]
        hist_kw = hist_kw or dict(
            bins=25,
            range=[np.nanmin(da.values), np.nanmax(da.values)],
        )
        x, y, _ = histogram(da, **hist_kw)
        for k, v in dict(ls='-', drawstyle='steps-mid').items():
            plot_kw.setdefault(k, v)
        plt.errorbar(x, y, **plot_kw)
        if add_label:
            plt.xlabel(
                f'{oet.plotting.plot.default_variable_labels().get(var, var)} [{oet.plotting.plot.get_unit_da(da)}]',
            )

    def summarize_stats(self, ds):
        return {
            field: summarize_stats(ds, field, path)
            for field, path in zip(
                oet.utils.to_str_tuple(ds.attrs['variables']),
                oet.utils.to_str_tuple(ds.attrs['source_files']),
            )
        }

    def process_masks(self) -> ty.Tuple[dict, xr.DataArray]:
        source_files = {}
        common_mask = None
        for path in self.mask_paths:  # type: ignore
            ds = oet.load_glob(path)
            # Source files may be non-unique!
            source_files[ds.attrs['variable_id']] = ds.attrs['file']
            common_mask = self.combine_masks(common_mask, ds)
        for other_path in self.other_paths:
            if other_path == '':  # pragma: no cover
                continue
            ds = oet.load_glob(other_path)
            # Source files may be non-unique!
            var = ds.attrs['variable_id']
            if var not in source_files:
                source_files[var] = ds.attrs['file']
        assert isinstance(common_mask, xr.DataArray)
        return source_files, common_mask

    def combine_masks(
        self,
        common_mask: ty.Optional[xr.DataArray],
        other_dataset: xr.Dataset,
        field: ty.Optional[str] = None,
    ) -> xr.DataArray:
        field = field or (
            'global_mask' if 'global_mask' in other_dataset else 'cell_area'
        )
        is_the_first_instance = common_mask is None
        if is_the_first_instance:
            return other_dataset[field].astype(np.bool_)
        if self.merge_method == 'logical_or':
            return common_mask | other_dataset[field].astype(np.bool_)

        raise NotImplementedError(
            f'No such method as {self.merge_method}',
        )  # pragma: no cover

    def add_table(self, *a, **kw):
        return add_table(*a, **kw)


def histogram(d, **kw):
    c, be = np.histogram(d, **kw)
    return (be[1:] + be[:-1]) / 2, c, be[1] - be[0]


def change_plt_table_height(increase_by=1.5):
    """Increase the height of rows in plt.table.

    Unfortunately, the options that you can pass to plt.table are insufficient to render a table
    that has rows with sufficient heights that work with a font that is not the default. From the
    plt.table implementation, I figured I could change these (rather patchy) lines in the source
    code:
    https://github.com/matplotlib/matplotlib/blob/b7dfdc5c97510733770429f38870a623426d0cdc/lib/matplotlib/table.py#L391

    Matplotlib version matplotlib==3.7.2
    """
    import matplotlib

    print('Change default plt.table row height')

    def _approx_text_height(self):
        return increase_by * (
            self.FONTSIZE / 72.0 * self.figure.dpi / self._axes.bbox.height * 1.2
        )

    matplotlib.table.Table._approx_text_height = _approx_text_height  # type: ignore


def add_table(
    res_f,
    tips,
    ax=None,
    fontsize=16,
    pass_color=(0.75, 1, 0.75),
    ha='bottom',
):
    ax = ax or plt.gcf().add_subplot(2, 2, 4)
    ax.axis('off')
    ax.axis('tight')

    table = ax.table(
        cellText=res_f.values,
        rowLabels=res_f.index,
        colLabels=res_f.columns,
        cellColours=[
            [(pass_color if v else [1, 1, 1]) for v in row] for row in tips.values
        ],
        loc=ha,
        colLoc='center',
        rowLoc='center',
        cellLoc='center',
    )
    table.set_fontsize(fontsize)


def result_table(res, thresholds=None, formats=None):
    thresholds = thresholds or default_thresholds()
    is_tip = pd.DataFrame(
        {
            k: {
                t: (thresholds[t][0](v, thresholds[t][1]) if v is not None else False)
                for t, v in d.items()
            }
            for k, d in res.items()
        },
    ).T

    formats = formats or dict(
        n_breaks='.0f',
        p_symmetry='.2%',
        p_dip='.1%',
        max_jump='.1f',
        n_std_global='.1f',
    )
    res_f = pd.DataFrame(res).T
    for k, f in formats.items():
        res_f[k] = res_f[k].map(f'{{:,{f}}}'.format)

    order = list(formats.keys())
    return res_f[order], is_tip[order]


def summarize_stats(ds, field, path):
    return {
        'n_breaks': oet.analyze.time_statistics.calculate_n_breaks(ds, field=field),
        'p_symmetry': oet.analyze.time_statistics.calculate_symmetry_test(
            ds,
            field=field,
        ),
        'p_dip': oet.analyze.time_statistics.calculate_dip_test(ds, field=field),
        'n_std_global': oet.analyze.time_statistics.n_times_global_std(
            ds=oet.load_glob(path).where(ds['global_mask']),
        ),
        'max_jump': oet.analyze.time_statistics.calculate_max_jump_in_std_history(
            ds=oet.load_glob(path).where(ds['global_mask']),
            mask=ds['global_mask'],
        ),
    }


if __name__ == '__main__':
    change_plt_table_height()
