# --- APPLY GRID LOGIC TO ACTUAL DATA ---
# We take the actual predictive data from the CSV and manually override it during the Grid Event
def apply_grid_override(df_day_subset):
    df_dyn = df_day_subset.copy()
    
    # Initialize all required columns upfront to prevent KeyErrors
    df_dyn['power_pred'] = df_dyn['power_pred_base']
    df_dyn['T_pred_dynamic'] = df_dyn['T_pred']
    df_dyn['safety_override_active'] = False
    df_dyn['energy_interval_pred'] = df_dyn['energy_interval_pred_base'] # <-- FIX: Added this line
    
    if not issue_load_shed or event_start_time is None:
        return df_dyn

    in_event = False
    temp_drift = 0.0 # Track how much temp deviates due to turning off AC
    
    for i in range(len(df_dyn)):
        t_stamp = df_dyn.index[i].time()
        
        # Determine if currently inside the event window
        if event_start_time <= event_end_time:
            is_grid_event = event_start_time <= t_stamp <= event_end_time
        else:
            is_grid_event = t_stamp >= event_start_time or t_stamp <= event_end_time
            
        current_temp_with_drift = df_dyn['T_pred'].iloc[i] + temp_drift

        if is_grid_event:
            if current_temp_with_drift >= max_temp_override:
                # OVERRIDE: Abort shed, turn AC back on (use base power/temp)
                df_dyn.loc[df_dyn.index[i], 'safety_override_active'] = True
                temp_drift = 0.0 
            else:
                # SHED LOAD: AC is off
                df_dyn.loc[df_dyn.index[i], 'power_pred'] = 0.0
                
                # Simulate simple temp drift upward toward outdoor temp while off
                outdoor_t = df_dyn['outdoor_temperature_C'].iloc[i]
                if current_temp_with_drift < outdoor_t:
                    temp_drift += (outdoor_t - current_temp_with_drift) * 0.05 
        else:
            # Recovery/Normal operation
            if temp_drift > 0:
                # Gradually recover back to the CSV's predicted baseline temp
                temp_drift *= 0.5 
            if temp_drift < 0.1:
                temp_drift = 0.0
                
        df_dyn.loc[df_dyn.index[i], 'T_pred_dynamic'] = df_dyn['T_pred'].iloc[i] + temp_drift

    # Recalculate Energy based on the dynamically altered power during an event
    df_dyn['energy_interval_pred'] = df_dyn['power_pred'] * (5/60) # Assuming 5 min intervals
    return df_dyn
