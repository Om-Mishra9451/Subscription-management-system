"""
SubscriptIQ Odoo Compatibility Adapter & Runtime Bridge
Provides transparent compatibility between native Odoo (20.0 / 19.0) and standalone execution environments.
Enables high-performance testing, benchmarks, and multi-environment deployment without altering business logic.
"""

import sys
import logging
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)

HAS_NATIVE_ODOO = False

try:
    import odoo
    from odoo import models, fields, api, _
    from odoo.exceptions import UserError, ValidationError, AccessError
    HAS_NATIVE_ODOO = True
    _logger.info("SubscriptIQ initialized with Native Odoo runtime (v%s)", getattr(odoo, 'release', {}).get('version', '20.0'))
except ImportError:
    HAS_NATIVE_ODOO = False
    _logger.info("SubscriptIQ initialized with Standalone Odoo Compatibility Layer")

    # Define standard Odoo exceptions
    class UserError(Exception):
        """Standard user-facing error."""
        pass

    class ValidationError(Exception):
        """Model validation constraint error."""
        pass

    class AccessError(Exception):
        """Security and role-based access violation."""
        pass

    def _(msg):
        """Translation helper."""
        return msg

    # Field definitions
    class Field:
        def __init__(self, string="", required=False, readonly=False, default=None, compute=None, store=True, copy=True, **kwargs):
            self.string = string
            self.required = required
            self.readonly = readonly
            self.default = default
            self.compute = compute
            self.store = store
            self.copy = copy
            self.kwargs = kwargs
            self.name = None

        def __set_name__(self, owner, name):
            self.name = name

    class Char(Field): pass
    class Text(Field): pass
    class Integer(Field):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.default is None and not kwargs.get('compute'):
                self.default = 0

    class Float(Field):
        def __init__(self, *args, digits=(16, 2), **kwargs):
            super().__init__(*args, **kwargs)
            self.digits = digits
            if self.default is None and not kwargs.get('compute'):
                self.default = 0.0

    class Monetary(Float):
        def __init__(self, *args, currency_field="currency_id", **kwargs):
            super().__init__(*args, **kwargs)
            self.currency_field = currency_field

    class Boolean(Field):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if self.default is None:
                self.default = False

    class Selection(Field):
        def __init__(self, selection=(), *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.selection = selection

    class Date(Field):
        @staticmethod
        def today():
            import datetime
            return datetime.date.today()

        @staticmethod
        def to_date(value):
            import datetime
            if not value:
                return None
            if isinstance(value, datetime.date):
                return value
            return datetime.date.fromisoformat(str(value)[:10])

    class Datetime(Field):
        @staticmethod
        def now():
            import datetime
            return datetime.datetime.now(datetime.timezone.utc)

        @staticmethod
        def to_datetime(value):
            import datetime
            if not value:
                return None
            if isinstance(value, datetime.datetime):
                return value
            return datetime.datetime.fromisoformat(str(value))

    class Many2one(Field):
        def __init__(self, comodel_name="", *args, ondelete="set null", **kwargs):
            super().__init__(*args, **kwargs)
            self.comodel_name = comodel_name
            self.ondelete = ondelete

    class One2many(Field):
        def __init__(self, comodel_name="", inverse_name="", *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.comodel_name = comodel_name
            self.inverse_name = inverse_name

    class Many2many(Field):
        def __init__(self, comodel_name="", relation=None, column1=None, column2=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.comodel_name = comodel_name

    class Binary(Field):
        def __init__(self, *args, attachment=True, **kwargs):
            super().__init__(*args, **kwargs)
            self.attachment = attachment

    class FieldsModule:
        Field = Field
        Char = Char
        Text = Text
        Integer = Integer
        Float = Float
        Monetary = Monetary
        Boolean = Boolean
        Selection = Selection
        Date = Date
        Datetime = Datetime
        Many2one = Many2one
        One2many = One2many
        Many2many = Many2many
        Binary = Binary

    fields = FieldsModule()

    # API Decorators
    class ApiModule:
        @staticmethod
        def model(func):
            func._api = 'model'
            return func

        @staticmethod
        def depends(*args):
            def decorator(func):
                func._depends = args
                return func
            return decorator

        @staticmethod
        def constrains(*args):
            def decorator(func):
                func._constrains = args
                return func
            return decorator

        @staticmethod
        def onchange(*args):
            def decorator(func):
                func._onchange = args
                return func
            return decorator

    api = ApiModule()

    # In-memory ORM simulation for Standalone/Testing
    MODEL_REGISTRY = {}

    class Environment:
        def __init__(self, registry=None, cr=None, uid=1, context=None, table_data=None, seq_counters=None):
            self.registry = registry or {}
            self.cr = cr
            self.uid = uid
            self.context = context or {'lang': 'en_US', 'tz': 'UTC'}
            self.companies = []
            self.user = None
            self.table_data = table_data if table_data is not None else {}
            self.seq_counters = seq_counters if seq_counters is not None else {}

        @property
        def company(self):
            return self['res.company'].browse(1)

        @company.setter
        def company(self, val):
            pass

        def __contains__(self, model_name):
            return model_name in self.registry or model_name in MODEL_REGISTRY

        def get(self, model_name, default=None):
            if model_name in self.registry or model_name in MODEL_REGISTRY:
                return self[model_name]
            return default

        def __getitem__(self, model_name):
            if model_name in self.registry:
                cls = self.registry[model_name]
            elif model_name in MODEL_REGISTRY:
                cls = MODEL_REGISTRY[model_name]
                self.registry[model_name] = cls
            else:
                cls = type(model_name, (Model,), {'_name': model_name})
                self.registry[model_name] = cls
            return RecordSet(cls, env=self)

        def ref(self, xml_id, raise_if_not_found=True):
            # Simulation XML ID resolver
            return RecordSet(Model, env=self, ids=[1])

    class RecordSet:
        def __init__(self, model_cls, env, ids=None, records=None):
            self._model_cls = model_cls
            self.env = env
            self._ids = list(ids) if ids else []
            self._records = list(records) if records else []
            if not self._records and self._ids:
                table = model_cls._get_table(env)
                self._records = [table.get(i) for i in self._ids if i in table]

        def __len__(self):
            return len(self._records)

        def __bool__(self):
            return len(self._records) > 0

        def __iter__(self):
            for r in self._records:
                yield RecordSet(self._model_cls, self.env, ids=[r.id], records=[r])

        def __getitem__(self, index):
            if isinstance(index, slice):
                sliced = self._records[index]
                return RecordSet(self._model_cls, self.env, ids=[r.id for r in sliced], records=sliced)
            item = self._records[index]
            return RecordSet(self._model_cls, self.env, ids=[item.id], records=[item])

        def __getattr__(self, name):
            if hasattr(self._model_cls, name):
                attr = getattr(self._model_cls, name)
                if isinstance(attr, property):
                    return attr.fget(self)
                if callable(attr):
                    import functools
                    return functools.partial(attr, self)
            if len(self._records) == 1:
                return getattr(self._records[0], name, False)
            elif len(self._records) == 0:
                return False
            raise ValueError(f"Expected singleton recordset for '{name}', got {len(self._records)} records")

        def __setattr__(self, name, value):
            if name in ('_model_cls', 'env', '_ids', '_records'):
                super().__setattr__(name, value)
            else:
                for r in self._records:
                    setattr(r, name, value)
                    if hasattr(self._model_cls, '_on_write'):
                        self._model_cls._on_write(r, {name: value})

        @property
        def id(self):
            return self._records[0].id if self._records else False

        @property
        def ids(self):
            return [r.id for r in self._records]

        def ensure_one(self):
            if len(self._records) != 1:
                raise ValueError(f"Expected singleton: {self._model_cls._name}({len(self._records)},)")
            return self

        def filtered(self, func):
            res = [r for r in self._records if func(RecordSet(self._model_cls, self.env, ids=[r.id], records=[r]))]
            return RecordSet(self._model_cls, self.env, ids=[r.id for r in res], records=res)

        def mapped(self, path):
            results = []
            for item in self:
                val = getattr(item, path)
                if isinstance(val, RecordSet):
                    results.extend(val)
                else:
                    results.append(val)
            return results

        def exists(self):
            table = self._model_cls._get_table(self.env)
            existing = [r for r in self._records if r.id in table]
            return RecordSet(self._model_cls, self.env, ids=[r.id for r in existing], records=existing)

        def create(self, vals):
            return self._model_cls.create_record(self.env, vals)

        def write(self, vals):
            if 'write' in self._model_cls.__dict__:
                return self._model_cls.write(self, vals)
            for r in self._records:
                for k, v in vals.items():
                    setattr(r, k, v)
                if hasattr(self._model_cls, '_on_write'):
                    self._model_cls._on_write(r, vals)
            return True

        def unlink(self):
            if 'unlink' in self._model_cls.__dict__:
                return self._model_cls.unlink(self)
            table = self._model_cls._get_table(self.env)
            for r in self._records:
                if r.id in table:
                    del table[r.id]
            self._records = []
            self._ids = []
            return True

        def search(self, domain=None, limit=None, order=None, offset=0):
            return self._model_cls.search_records(self.env, domain, limit, order, offset)

        def search_count(self, domain=None):
            return len(self.search(domain))

        def browse(self, ids):
            if isinstance(ids, int):
                ids = [ids]
            table = self._model_cls._get_table(self.env)
            records = [table[i] for i in ids if i in table]
            return RecordSet(self._model_cls, self.env, ids=[r.id for r in records], records=records)

        def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=None, lazy=True):
            return self._model_cls.read_group_records(self.env, domain, fields, groupby)

        def sudo(self):
            # Security elevation simulation
            new_env = Environment(self.env.registry, self.env.cr, uid=1, context=dict(self.env.context, superuser=True))
            return RecordSet(self._model_cls, new_env, self._ids, self._records)

        def with_context(self, *args, **kwargs):
            ctx = dict(self.env.context)
            if args and isinstance(args[0], dict):
                ctx.update(args[0])
            ctx.update(kwargs)
            new_env = Environment(self.env.registry, self.env.cr, uid=self.env.uid, context=ctx)
            return RecordSet(self._model_cls, new_env, self._ids, self._records)

        def with_company(self, company):
            company_id = company.id if hasattr(company, 'id') else company
            new_env = Environment(self.env.registry, self.env.cr, uid=self.env.uid, context=dict(self.env.context, allowed_company_ids=[company_id]))
            return RecordSet(self._model_cls, new_env, self._ids, self._records)

        def __repr__(self):
            return f"{self._model_cls._name}({self._ids})"

    class BaseRecord:
        """Underlying storage record instance."""
        def __init__(self, id_val, vals):
            self.id = id_val
            self.create_date = Datetime.now()
            self.write_date = Datetime.now()
            for k, v in vals.items():
                setattr(self, k, v)

    class Model:
        _name = "base"
        _description = "Base Model"
        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            name = cls.__dict__.get('_name')
            inherit = cls.__dict__.get('_inherit')
            if not name and inherit:
                cls._name = inherit
                name = inherit
            if name:
                MODEL_REGISTRY[name] = cls
            if inherit:
                MODEL_REGISTRY[inherit] = cls

        @classmethod
        def _get_table(cls, env=None):
            if env and hasattr(env, 'table_data'):
                if cls._name not in env.table_data:
                    env.table_data[cls._name] = {}
                return env.table_data[cls._name]
            if cls._name not in Model._table_data:
                Model._table_data[cls._name] = {}
            return Model._table_data[cls._name]

        @classmethod
        def create_record(cls, env, vals):
            table = cls._get_table(env)
            seq_map = env.seq_counters if (env and hasattr(env, 'seq_counters')) else Model._seq_counters
            new_id = seq_map.get(cls._name, 0) + 1
            seq_map[cls._name] = new_id

            # Apply defaults from class attributes
            data = {}
            dummy_record = RecordSet(cls, env)
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if isinstance(attr, Field):
                    if attr.default is not None:
                        if callable(attr.default):
                            try:
                                data[attr_name] = attr.default(dummy_record)
                            except TypeError:
                                data[attr_name] = attr.default()
                        else:
                            data[attr_name] = attr.default
            data.update(vals)
            record = BaseRecord(new_id, data)
            table[new_id] = record

            recordset = RecordSet(cls, env, ids=[new_id], records=[record])
            # Execute compute fields if any
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if isinstance(attr, Field) and attr.compute:
                    compute_fn = getattr(cls, attr.compute, None)
                    if callable(compute_fn):
                        compute_fn(recordset)

            return recordset

        @classmethod
        def search_records(cls, env, domain=None, limit=None, order=None, offset=0):
            table = cls._get_table(env)
            records = list(table.values())

            # Basic domain filtering
            if domain:
                filtered = []
                for r in records:
                    match = True
                    for cond in domain:
                        if not isinstance(cond, (list, tuple)) or len(cond) < 3:
                            continue
                        f_name, op, val = cond[0], cond[1], cond[2]
                        rec_val = getattr(r, f_name, None)
                        # Handle Many2one comparisons
                        if hasattr(rec_val, 'id'):
                            rec_val = rec_val.id
                        if hasattr(val, 'id'):
                            val = val.id

                        if op == '=' and rec_val != val:
                            match = False
                            break
                        elif op == '!=' and rec_val == val:
                            match = False
                            break
                        elif op == 'in' and rec_val not in val:
                            match = False
                            break
                        elif op == 'not in' and rec_val in val:
                            match = False
                            break
                        elif op == '>' and not (rec_val is not None and rec_val > val):
                            match = False
                            break
                        elif op == '>=' and not (rec_val is not None and rec_val >= val):
                            match = False
                            break
                        elif op == '<' and not (rec_val is not None and rec_val < val):
                            match = False
                            break
                        elif op == '<=' and not (rec_val is not None and rec_val <= val):
                            match = False
                            break
                        elif op == 'ilike' and not (isinstance(rec_val, str) and str(val).lower() in rec_val.lower()):
                            match = False
                            break
                    if match:
                        filtered.append(r)
                records = filtered

            if offset:
                records = records[offset:]
            if limit:
                records = records[:limit]

            ids = [r.id for r in records]
            return RecordSet(cls, env, ids=ids, records=records)

        @classmethod
        def read_group_records(cls, env, domain, fields, groupby):
            records = cls.search_records(env, domain)
            group_map = {}
            for r in records:
                grp_val = getattr(r, groupby[0]) if groupby else 'all'
                if grp_val not in group_map:
                    group_map[grp_val] = []
                group_map[grp_val].append(r)

            result = []
            for grp_val, grp_records in group_map.items():
                entry = {groupby[0]: grp_val, f"{groupby[0]}_count": len(grp_records)}
                for f in fields:
                    if f.endswith(':sum'):
                        fname = f.split(':')[0]
                        total = sum(getattr(r, fname, 0.0) or 0.0 for r in grp_records)
                        entry[fname] = total
                result.append(entry)
            return result

    class TransientModel(Model):
        _transient = True

    class ModelsModule:
        Model = Model
        TransientModel = TransientModel
        BaseRecord = BaseRecord

    models = ModelsModule()
    BaseRecord = BaseRecord

# Precise monetary rounding helper
def round_currency(amount, precision=2):
    """Accurately round monetary value using Decimal HALF_UP."""
    if amount is None:
        return Decimal("0.00")
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    quantizer = Decimal('10') ** -precision
    return amount.quantize(quantizer, rounding=ROUND_HALF_UP)
