# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
        if not filters: filters = {}
        salary_slips = get_salary_slips(filters)
        columns, earning_types, ded_types = get_columns(salary_slips)
        ss_earning_map = get_ss_earning_map(salary_slips)
        ss_ded_map = get_ss_ded_map(salary_slips)

        department_all = {}
        data = []
        for ss in salary_slips:
		grade,first_name,last_name,salary_mode = frappe.db.get_value("Employee", ss.employee,["grade", "first_name","last_name","salary_mode"])
                row = [ss.employee, str(first_name)+' '+str(last_name), ss.designation,grade,ss.total_working_days,ss.leave_without_pay]


                for e in earning_types:
                        row.append(ss_earning_map.get(ss.name, {}).get(e))

                row += [ss.gross_pay]

                for d in ded_types:
                        row.append(ss_ded_map.get(ss.name, {}).get(d))

                row += [ss.total_deduction, ss.net_pay,salary_mode]

                data.append(row)
                
                if department_all.has_key(ss.department):
                        dep_data = department_all[ss.department]

                        dep_data = dep_data.append(row)

                
                else:
                        
                        department_all[ss.department] = [row]
                        




        section_data = []
        total_sum_dep = [0 for x in range(len(row))]
        for key,values in department_all.iteritems():
                        
                        size = len(values[0])
                        
                        m = ''
                        x=[]
                        for i in range(size-3):
                                x.append(m)
                        
                        row_new = [key,"Head Count",str(len(values))]
                        row_new.extend(x)

                        section_data.append(row_new)
                        
                        sum_dep = [0 for x in range(len(values[0]))]
                        for value in values:
                                section_data.append(value)
                                for ind,amount in enumerate(value):
                                        if type(amount) is float:
                                                sum_dep[ind]= round(sum_dep[ind] + amount,2)
						total_sum_dep[ind]= round(total_sum_dep[ind] + amount,2)
                        sum_dep[0] = ''
			sum_dep[1] = ''
			sum_dep[2] = key + ' Total'
                        sum_dep[3] = ''
			sum_dep[-1]= ''

                        section_data.append(sum_dep)
                        blank = ['' for x in range(len(values[0]))]
                        section_data.append(blank)

	total_sum_dep[0] = ''
	total_sum_dep[1] = ''
	total_sum_dep[2] = 'Total'
        total_sum_dep[3] = ''
	total_sum_dep[-1] = ''
	section_data.append(total_sum_dep)
        return columns,section_data

def get_columns(salary_slips):
        """
        columns = [
                _("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140", _("Branch") + ":Link/Branch:120",
                _("Department") + ":Link/Department:120", _("Designation") + ":Link/Designation:120",
                _("Company") + ":Link/Company:120", _("Start Date") + "::80", _("End Date") + "::80", _("Leave Without Pay") + ":Float:130",
                _("Payment Days") + ":Float:120"
        ]
        """
        columns = [
                _("Employee") + ":Link/Employee:120", _("Employee Name") + "::140", _("Position") + "::160",_("Grade") + "::80", _("Days Worked") + ":Currency:100",_("VL Days") + ":Currency:60"]

        salary_components = {_("Earning"): [], _("Deduction"): []}

        for component in frappe.db.sql("""select distinct sd.salary_component, sc.type
                from `tabSalary Detail` sd, `tabSalary Component` sc
                where sc.name=sd.salary_component and sd.amount != 0 and sd.parent in (%s)""" %
                (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1):
                salary_components[_(component.type)].append(component.salary_component)

        columns = columns + [(e + ":Currency:120") for e in salary_components[_("Earning")]] + \
                [_("Gross Pay") + ":Currency:120"] + [(d + ":Currency:120") for d in salary_components[_("Deduction")]] + \
                [_("Total Deduction") + ":Currency:120", _("Net Pay") + ":Currency:120",_("Method") + ":Data:120"]

        return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

def get_salary_slips(filters):
        filters.update({"from_date": filters.get("date_range")[0], "to_date":filters.get("date_range")[1]})
        conditions, filters = get_conditions(filters)
        salary_slips = frappe.db.sql("""select * from `tabSalary Slip` %s order by employee""" % conditions, filters, as_dict=1)
	
        if not salary_slips:
                frappe.throw(_("No salary slip found between {0} and {1}").format(
                        filters.get("from_date"), filters.get("to_date")))
        return salary_slips

def get_conditions(filters):
        conditions = ""
	if filters.get("slip_status") == "Draft":
                conditions += "where docstatus = 0"
        else:
                conditions += "where docstatus = 1"

        if filters.get("date_range"): conditions += " and start_date >= %(from_date)s"
        if filters.get("date_range"): conditions += " and end_date <= %(to_date)s"
        if filters.get("company"): conditions += " and company = %(company)s"
        if filters.get("employee"): conditions += " and employee = %(employee)s"
        if filters.get("department"): conditions += " and department = %(department)s"
        if filters.get("designation"): conditions += " and designation = %(designation)s"
	
        return conditions, filters

def get_ss_earning_map(salary_slips):
        ss_earnings = frappe.db.sql("""select parent, salary_component, amount
                from `tabSalary Detail` where parent in (%s)""" %
                (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

        ss_earning_map = {}
        for d in ss_earnings:
                ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
                ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

        return ss_earning_map

def get_ss_ded_map(salary_slips):
        ss_deductions = frappe.db.sql("""select parent, salary_component, amount
                from `tabSalary Detail` where parent in (%s)""" %
                (', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

        ss_ded_map = {}
        for d in ss_deductions:
                ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
                ss_ded_map[d.parent][d.salary_component] = flt(d.amount)

        return ss_ded_map




'''
from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	salary_slips = get_salary_slips(filters)
	columns, earning_types, ded_types = get_columns(salary_slips)
	ss_earning_map = get_ss_earning_map(salary_slips)
	ss_ded_map = get_ss_ded_map(salary_slips)


	data = []
	for ss in salary_slips:
		row = [ss.name, ss.employee, ss.employee_name, ss.branch, ss.department, ss.designation,
			ss.company, ss.start_date, ss.end_date, ss.leave_withut_pay, ss.payment_days]

		if not ss.branch == None:columns[3] = columns[3].replace('-1','120')
		if not ss.department  == None: columns[4] = columns[4].replace('-1','120')
		if not ss.designation  == None: columns[5] = columns[5].replace('-1','120')
		if not ss.leave_withut_pay  == None: columns[9] = columns[9].replace('-1','130')
			

		for e in earning_types:
			row.append(ss_earning_map.get(ss.name, {}).get(e))

		row += [ss.gross_pay]

		for d in ded_types:
			row.append(ss_ded_map.get(ss.name, {}).get(d))

		row += [ss.total_deduction, ss.net_pay]

		data.append(row)

	return_list = []
	last_row = []
	department_list = frappe.get_all('Department',fields = ["name"])
	department_list  = list([dept['name'] for dept in department_list])
	
	for dept in department_list:
		department_wise = []
		for row in data:
			if dept == row[4]:

				department_wise.append(row)
			
		if department_wise:
			dept_list = []
			dept_row = get_department_row(department_wise)
			total_row = get_total_row(department_wise)
			department_wise.append(total_row)
			last_row = get_last_row(last_row,total_row)
			dept_list.append(dept_row)
			dept_list.extend(department_wise)
			return_list.extend(dept_list)

	return_list.append(last_row)
	return columns, return_list	

def get_columns(salary_slips):
	"""
	columns = [
		_("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140", _("Branch") + ":Link/Branch:120",
		_("Department") + ":Link/Department:120", _("Designation") + ":Link/Designation:120",
		_("Company") + ":Link/Company:120", _("Start Date") + "::80", _("End Date") + "::80", _("Leave Without Pay") + ":Float:130",
		_("Payment Days") + ":Float:120"
	]
	"""
	columns = [
		_("Salary Slip ID") + ":Link/Salary Slip:150",_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140", _("Branch") + ":Link/Branch:-1",
		_("Department") + ":Link/Department:-1", _("Designation") + ":Link/Designation:-1",
		_("Company") + ":Link/Company:120", _("Start Date") + "::80", _("End Date") + "::80", _("Leave Without Pay") + ":Float:-1",
		_("Payment Days") + ":Float:120"
	]	

	salary_components = {_("Earning"): [], _("Deduction"): []}

	for component in frappe.db.sql("""select distinct sd.salary_component, sc.type
		from `tabSalary Detail` sd, `tabSalary Component` sc
		where sc.name=sd.salary_component and sd.amount != 0 and sd.parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1):
		salary_components[_(component.type)].append(component.salary_component)

	columns = columns + [(e + ":Currency:120") for e in salary_components[_("Earning")]] + \
		[_("Gross Pay") + ":Currency:120"] + [(d + ":Currency:120") for d in salary_components[_("Deduction")]] + \
		[_("Total Deduction") + ":Currency:120", _("Net Pay") + ":Currency:120"]

	return columns, salary_components[_("Earning")], salary_components[_("Deduction")]

def get_salary_slips(filters):
	filters.update({"from_date": filters.get("date_range")[0], "to_date":filters.get("date_range")[1]})
	conditions, filters = get_conditions(filters)
	salary_slips = frappe.db.sql("""select * from `tabSalary Slip` where docstatus = 1 %s
		order by employee""" % conditions, filters, as_dict=1)

	if not salary_slips:
		frappe.throw(_("No salary slip found between {0} and {1}").format(
			filters.get("from_date"), filters.get("to_date")))
	return salary_slips

def get_conditions(filters):
	conditions = ""
	if filters.get("date_range"): conditions += " and start_date >= %(from_date)s"
	if filters.get("date_range"): conditions += " and end_date <= %(to_date)s"
	if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_ss_earning_map(salary_slips):
	ss_earnings = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_earning_map = {}
	for d in ss_earnings:
		ss_earning_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
		ss_earning_map[d.parent][d.salary_component] = flt(d.amount)

	return ss_earning_map

def get_ss_ded_map(salary_slips):
	ss_deductions = frappe.db.sql("""select parent, salary_component, amount
		from `tabSalary Detail` where parent in (%s)""" %
		(', '.join(['%s']*len(salary_slips))), tuple([d.name for d in salary_slips]), as_dict=1)

	ss_ded_map = {}
	for d in ss_deductions:
		ss_ded_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, [])
		ss_ded_map[d.parent][d.salary_component] = flt(d.amount)

	return ss_ded_map

def get_total_row(dept_list):
	total_row = [u'', u'', u'', u'', u'', u'', u'',u'',u'',u'',u'',0.0, 0.0,0.0, 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
	
	for row in dept_list:
		for i in range(11,len(row)):
			total_row[i] = total_row[i] + flt(row[i])
	return total_row


def get_last_row(last_row,total_row):

	if last_row:
		for i in range(11,len(total_row)):
				last_row[i] = last_row[i] + flt(total_row[i])
		return last_row
	else:
		last_row = [u'', u'', u'', u'', u'', u'', u'',u'',u'',u'',u'',0.0, 0.0,0.0, 0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]
		for i in range(11,len(total_row)):
				last_row[i] = last_row[i] + flt(total_row[i])
		return last_row

def get_department_row(department_wise):
	dept = ''
	for row in department_wise:
		dept = row[4]
	return ['<b>'+dept+'</b>', u'', u'', u'', u'', u'', u'',u'',u'',u'',u'',u'', u'',u'', u'',u'',u'',u'',u'',u'',u'',u'']

'''
