# -*- coding: utf-8 -*-
import unittest
import optim_esm_tools._test_utils
from optim_esm_tools.analyze import region_finding
import tempfile
import os


class Work(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for data_name in ['ssp585', 'piControl']:
            cls.get_path(data_name)

    @staticmethod
    def get_path(data_name, refresh=True):
        path = optim_esm_tools._test_utils.get_file_from_pangeo(
            data_name, refresh=refresh
        )
        year_path = optim_esm_tools._test_utils.year_means(path, refresh=refresh)
        print(year_path)
        assert year_path
        assert os.path.exists(year_path)
        return year_path

    def test_max_region(self, make='MaxRegion', new_opt=None, skip_save=True):
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
                read_ds_kw=dict(_file_name=tail),
                transform=True,
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
            'ProductPercentiles', new_opt=dict(cluster_method='weighted')
        )
