import anvil.tables as tables
from functools import wraps


def in_transaction(*d_args, **d_kwargs):
    only_arg_is_func_to_decorate = (len(d_args) == 1 and callable(d_args[0]) and not d_kwargs)
    if only_arg_is_func_to_decorate:
        func_to_decorate = d_args[0]
        tables_in_transaction = tables.in_transaction
    else:
        tables_in_transaction = tables.in_transaction(*d_args, **d_kwargs)
    
    def decorator(func):
        @wraps(func)
        def out_function(*args, **kwargs):
            # init. caching, clearing any prev. cache
            
            result = tables_in_transaction(func)(*args, **kwargs) # Call the original function
            
            # clear cache
            
            return result
        
        return out_function
    
    # Return the decorator function if called with decorator args
    if only_arg_is_func_to_decorate:
        return decorator(func_to_decorate)
    else:
        return decorator