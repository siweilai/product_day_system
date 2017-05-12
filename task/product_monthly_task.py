# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time
from openerp.osv import fields, osv, expression


class product_monthly(osv.Model):
    _inherit = 'product.monthly'

    def do_run_compute_product_monthly_task(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        # 一、 todo 查询数据库中的 product_monthly_line 中state = 'draft'的明细id 和 product_monthly的id:
        # todo 当前日期:
        global today_date
        today_date = (str(datetime.now()))[0:10]
        # 1.1、todo 获取当前月结时间：
        date_local_day = self.monthly_line_name(cr, uid, context)
        # 1.2、todo 获取当前product_monthly_line 中state = 'draft' 和 name=date_local_day的明细id：
        line_sql = """SELECT pm.id,pml.id AS pml_id FROM product_monthly_line pml
                    LEFT JOIN product_monthly pm ON pml.fiscalyear_id = pm.id
                    WHERE pml.state = 'draft' AND pml.name = %s"""
        cr.execute(line_sql, (date_local_day,))
        return_line_arr = cr.dictfetchall()
        if return_line_arr and len(return_line_arr) > 0:
            pm_id = return_line_arr[0]['id']
            pml_id = return_line_arr[0]['pml_id']
        else:
            # todo 打开本月的会计期间
            update_line_sql = """ UPDATE product_monthly_line SET state = 'draft' WHERE name = %s"""
            cr.execute(update_line_sql, (date_local_day,))
            cr.commit()
            line_second_sql = """SELECT pm.id,pml.id AS pml_id FROM product_monthly_line pml
                    LEFT JOIN product_monthly pm ON pml.fiscalyear_id = pm.id
                    WHERE pml.state = 'draft' AND pml.name = %s"""
            cr.execute(line_second_sql, (date_local_day,))
            return_line_second_arr = cr.dictfetchall()
            pm_id = return_line_second_arr[0]['id']
            pml_id = return_line_second_arr[0]['pml_id']
            # todo 关闭其他月的会计期间
            update_done_sql = """UPDATE product_monthly_line SET state = 'done' WHERE name <> %s"""
            cr.execute(update_done_sql, (date_local_day,))
            cr.commit()
        # 2、todo 获取当前product_monthly_line 中最大的id：
        line_max_sql = """SELECT MAX(pml.id) AS max_id FROM product_monthly_line pml """
        cr.execute(line_max_sql)
        return_line_max_arr = cr.dictfetchall()
        max_id = return_line_max_arr[0]['max_id']
        data = {'pml_id': pml_id, 'date_local_day': date_local_day}
        if pml_id < max_id:
            self.compute_product_monthly(cr, uid, [pm_id], data, context)
        else:
            # 3、todo 在产品月结中创建新的会计年度：
            self.compute_create_product_monthly(cr, uid, data, context)
            self.compute_product_monthly(cr, uid, [pm_id], data, context)
        # 4、todo 对旧的会计年度，进行审核，完成本年的会计年度：
        if today_date[-5:] == '01-01':
            self.compute_closed_product_monthly(cr, uid, [pm_id], data, context)

    def compute_product_monthly(self, cr, uid, ids, data, context=None):
        pml_id = data['pml_id']
        # TODO 取得当前id的上一个id：
        next_id_sql = """SELECT id FROM product_monthly_line WHERE id < %s ORDER BY id DESC LIMIT 1"""
        cr.execute(next_id_sql, (pml_id,))
        return_next_id_arr = cr.dictfetchall()
        next_id = return_next_id_arr[0]['id']
        if today_date[-2:] == '01':
            # todo 第一步:关闭上月的会计期间，打开本月的会计期间：
            update_done_sql = """UPDATE product_monthly_line SET state = 'done' WHERE id = %s """
            cr.execute(update_done_sql, (next_id,))
            cr.commit()
            update_done_sql = """UPDATE product_monthly_line SET state = 'draft' WHERE id = %s """
            cr.execute(update_done_sql, (pml_id,))
            cr.commit()

        product_monthly = self.browse(cr, uid, ids[0], context=context)
        # todo 第一步：生成本年度产品：
        product_monthly.all_product()
        # todo 第二步:计算产品金额：
        product_monthly.product_amount_total()
        # todo 第三步:计算月一次加权平均：
        product_monthly.year_product_average()
        return True

    def compute_create_product_monthly(self, cr, uid, data, context=None):
        # todo 创建新的会计产品月结年度
        date_local_day = data['date_local_day']
        year = date_local_day[0:4]
        parm = {
            'name': str(int(year) + 1),
            'date_start': str(int(year) + 1) + '-01-01',
            'date_stop': str(int(year) + 1) + '-12-31',
            'company_id': 1,
            'pool_id': 1,
        }
        monthly_id = self.create(cr, uid, parm, context=context)
        product_monthly = self.browse(cr, uid, monthly_id, context)
        # todo 创建月度客户回收期间：
        product_monthly.create_period()
        # todo 关闭其他月的会计期间
        update_done_sql = """UPDATE product_monthly_line SET state = 'done' WHERE name <> %s """
        cr.execute(update_done_sql, (date_local_day,))
        cr.commit()
        return True

    def compute_closed_product_monthly(self, cr, uid, ids, data, context=None):
        # TODO 取得当前id的上一个id：
        last_id_sql = """SELECT id FROM product_monthly WHERE id < %s ORDER BY id DESC LIMIT 1"""
        cr.execute(last_id_sql, (ids[0],))
        return_last_id_arr = cr.dictfetchall()
        last_id = return_last_id_arr[0]['id']
        # todo 关闭旧的会计产品月结年度
        product_monthly = self.browse(cr, uid, last_id, context)
        product_monthly.bnt_done()
        return True

    def monthly_line_name(self, cr, uid, context=None):
        # todo 当前会计期间的名称
        date_local = datetime.now()
        date_local_day = (str(date_local))[0:7]
        # date_local_day = (str(date_local))[0:8]
        # date_local_day = date_local_day + '01 00:00:00'
        # # todo 判断时间
        # # todo 先对月进行判断，如果月是1，就对年的值进行修改：
        # if str(date_local)[0:7] == date_local_day[0:7]:
        #     if int(date_local_day[5:7]) > 1 and int(date_local_day[5:7]) <= 10:
        #         year = date_local_day[0:4]
        #         month = str(int(date_local_day[5:7]) - 1)
        #         date_local_day = year + '-0' + month
        #     elif int(date_local_day[5:7]) > 10:
        #         year = date_local_day[0:4]
        #         month = str(int(date_local_day[5:7]) - 1)
        #         date_local_day = year + '-' + month
        #     else:
        #         year = str(int(date_local_day[0:4]) - 1)
        #         month = '12'
        #         date_local_day = year + '-' + month
        return date_local_day
