import unittest

from hape_test_base import HapeTestBase
from hape_libs.common import HapeCommon
from hape_libs.testlib.main import test_main

import time
import random

class HapeTableCatalogTest(unittest.TestCase, HapeTestBase):
    def setUp(self):
        self.init()

    def tearDown(self):
        self.destory()

    def test_table_catalog(self):
        ## start
        self.assertTrue(self.hape_cluster.start_hippo_appmaster(HapeCommon.HAVENASK_KEY))

        ## table rw
        self._run_direct_tables_case("in0")
        self._run_direct_tables_case("in1")
        self._run_direct_table_delete("in0")
        self._run_direct_table_rw("in1")
        catalog_manager = self.hape_cluster.get_suez_catalog_manager()
        tables = list(catalog_manager.list_table().keys())
        self.assertTrue("in1" in tables)
        self.assertFalse("in2" in tables)


        self.assertTrue(self.hape_cluster.stop_hippo_appmaster(HapeCommon.HAVENASK_KEY))
        self.assertTrue(self.hape_cluster.stop_hippo_appmaster(HapeCommon.SWIFT_KEY))

        self.assertTrue(self.zk_wrapper.check_zk(path=self.hape_cluster.suez_appmaster.hippo_zk_full_path()))
        self.assertTrue(self.zk_wrapper.check_zk(path=self.hape_cluster.suez_appmaster.service_zk_full_path()))

    def _run_direct_tables_case(self, table):
        self._run_direct_table_create(table)
        self._run_direct_table_rw(table)

    def _run_direct_table_rw(self, table):
        column_names = ['id', 'hits', 'createtime']
        column_types = ['uint32', 'uint32', 'uint64']
        datas = [
            [0, random.randint(0, 10000), random.randint(0, 10000)],
            [1, random.randint(0, 10000), random.randint(0, 10000)],
            [2, random.randint(0, 10000), random.randint(0, 10000)]
        ]
        fields_str = ','.join(column_names)
        address = self.hape_cluster.suez_appmaster.get_qrs_ips()[0] + ":" + self.hape_cluster.suez_appmaster.get_qrs_httpport()
        # insert
        values_str = ','.join(['?' for i in range(len(column_names))])
        for i in range(len(datas)):
            dynamic_params = ','.join(['\\"{}\\"'.format(d) for d in datas[i]])
            query = '''INSERT into {} ({}) values({})&&kvpair=timeout:500000;searchInfo:true;exec.leader.prefer.level:1;databaseName:database;dynamic_params:[[{}]]'''.format(table, fields_str, values_str, dynamic_params)
            data = self.search_sql(address, query)
            self.assert_result(data, ['ROWCOUNT'], ['int64'], [[1]])

        # update one field
        query = '''UPDATE {table} SET {assignment} WHERE {condition}&&kvpair=timeout:500000;searchInfo:true;exec.leader.prefer.level:1;databaseName:database;'''.format(table=table, assignment='hits=123', condition="id =1")
        data = self.search_sql(address, query)
        time.sleep(5)
        # search
        query = '''SELECT {} FROM {} where id={}&&kvpair=searchInfo:true;exec.leader.prefer.level:1;timeout:50000;databaseName:database;'''.format(fields_str, table, 1)
        data = self.search_sql(address, query)
        updated_data = datas[1]
        updated_data[1] = 123
        self.assert_result(data, column_names, column_types, [updated_data])

        # update multi field
        query = '''UPDATE {table} SET {assignment} WHERE {condition}&&kvpair=timeout:500000;searchInfo:true;exec.leader.prefer.level:1;databaseName:database;'''.format(table=table, assignment='hits=123,createtime=4321', condition="id = 1")
        data = self.search_sql(address, query)
        time.sleep(5)
        # search
        query = '''SELECT {} FROM {} where id={}&&kvpair=searchInfo:true;exec.leader.prefer.level:1;timeout:50000;databaseName:database;'''.format(fields_str, table, 1)
        data = self.search_sql(address, query)
        updated_data = datas[1]
        updated_data[1] = 123
        updated_data[2] = 4321
        self.assert_result(data, column_names, column_types, [updated_data])

        # check other doc not change
        for i in [0, 2]:
            query = '''SELECT {} FROM {} where id={}&&kvpair=searchInfo:true;exec.leader.prefer.level:1;timeout:50000;databaseName:database;'''.format(fields_str, table, i)
            data = self.search_sql(address, query)
            self.assert_result(data, column_names, column_types, [datas[i]])

    def _run_direct_table_delete(self, table):
        self.assertTrue(self.hape_cluster.delete_table(table))

    def _run_direct_table_create(self, table):
        self.assertTrue(self.hape_cluster.create_table(table, 1, self.testdata_root + "/in0_schema.json", None))

test_main()