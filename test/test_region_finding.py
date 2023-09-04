import os
import tempfile
import unittest

import optim_esm_tools._test_utils
from optim_esm_tools.analyze import region_finding
from optim_esm_tools.analyze.cmip_handler import read_ds


class Work(unittest.TestCase):
    """Note of caution!

    _CACHE_TRUE=True can lead to funky behavior!
    """

    @classmethod
    def setUpClass(cls):
        for data_name in ['ssp585', 'piControl']:
            cls.get_path(data_name)

    @staticmethod
    def get_path(data_name, refresh=True):
        return optim_esm_tools._test_utils.get_path_for_ds(data_name, refresh=refresh)

    def test_max_region(self, make='MaxRegion', new_opt=None, skip_save=True):
        # sourcery skip: dict-assign-update-to-union
        cls = getattr(region_finding, make)
        file_path = self.get_path('ssp585', refresh=False)

        head, tail = os.path.split(file_path)
        extra_opt = dict(
            time_series_joined=True,
            scatter_medians=True,
            percentiles=50,
            search_kw=dict(required_file=tail),
        )
        if new_opt:
            extra_opt.update(new_opt)
        with tempfile.TemporaryDirectory() as temp_dir:
            save_kw = dict(
                save_in=temp_dir,
                sub_dir=None,
                file_types=('png',),
                dpi=25,
                skip=skip_save,
            )

            region_finder = cls(
                path=head,
                read_ds_kw=dict(
                    _file_name=tail,
                    _cache=os.environ.get('_CACHE_TRUE', 0),
                ),
                save_kw=save_kw,
                extra_opt=extra_opt,
            )
            region_finder.show = False

            region_finder.workflow()
            return region_finder

    def test_max_region_wo_time_series(self):
        self.test_max_region('MaxRegion', new_opt=dict(time_series_joined=False))

    def test_percentiles(self):
        self.test_max_region('Percentiles', new_opt=dict(time_series_joined=False))

    def test_percentiles_weighted(self):
        self.test_max_region('Percentiles', new_opt=dict(cluster_method='weighted'))

    def test_percentiles_history(self):
        region_finder = self.test_max_region('PercentilesHistory')
        with self.assertRaises(RuntimeError):
            # We only have piControl (so this should fail)!
            region_finder.find_historical('historical')

    def test_percentiles_product(self):
        self.test_max_region('ProductPercentiles', skip_save=False)

    def test_local_history(self):
        self.test_max_region('LocalHistory')

    def test_percentiles_product_weighted(self):
        self.test_max_region(
            'ProductPercentiles',
            new_opt=dict(cluster_method='weighted'),
        )

    def test_error_message(self, make='MaxRegion'):
        cls = getattr(region_finding, make)
        file_path = self.get_path('ssp585', refresh=False)
        head, tail = os.path.split(file_path)
        ds = read_ds(
            head,
            _file_name=tail,
        )
        region = cls(data_set=ds)
        with self.assertRaises(ValueError):
            region.check_shape(ds['cell_area'].T)

    def test_iter_product_percentiles(self):
        self.test_max_region('IterProductPercentiles')

    # def test_iter_local_history(self):
    #     self.test_max_region('IterLocalHistory')

    def test_iter_percentiles(self):
        self.test_max_region('IterPercentiles')

    def test_iter_raises(self):
        with self.assertRaises(NotImplementedError):
            self.test_max_region(
                'IterProductPercentiles',
                new_opt=dict(cluster_method='weighted'),
            )
        # with self.assertRaises(NotImplementedError):
        #     self.test_max_region('IterLocalHistory', new_opt=dict(cluster_method='weighted'))
        with self.assertRaises(NotImplementedError):
            self.test_max_region(
                'IterPercentiles',
                new_opt=dict(cluster_method='weighted'),
            )
