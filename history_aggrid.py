import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, ColumnsAutoSizeMode

def prepare_data_for_aggrid(df):
    """
    Prepare DataFrame for AgGrid by ensuring all data is in a format that AgGrid can handle.
    
    Args:
        df: Input DataFrame to prepare
        
    Returns:
        Tuple of (processed_df, column_defs)
    """
    import pandas as pd
    import numpy as np
    
    if df is None or df.empty:
        return pd.DataFrame(), []
    
    try:
        # Create a clean copy of the DataFrame
        clean_df = df.copy()
        
        # Ensure all column names are strings
        clean_df.columns = clean_df.columns.astype(str)
        
        # Convert all datetime columns to string
        datetime_cols = clean_df.select_dtypes(include=['datetime64']).columns
        for col in datetime_cols:
            clean_df[col] = clean_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Convert all columns to string to avoid serialization issues
        for col in clean_df.columns:
            if pd.api.types.is_object_dtype(clean_df[col]):
                # Handle object/string columns
                clean_df[col] = clean_df[col].astype(str)
            elif pd.api.types.is_numeric_dtype(clean_df[col]):
                # Convert numeric columns to string, handling NaN/None values
                clean_df[col] = clean_df[col].astype('object').fillna('').astype(str)
            else:
                # For other types, convert to string
                clean_df[col] = clean_df[col].astype(str)
        
        # Generate column definitions
        column_defs = []
        for col in clean_df.columns:
            col_def = {
                'field': col,
                'headerName': col.replace('_', ' ').title(),
                'sortable': col not in ['Edit', 'Delete'],
                'filter': col not in ['Edit', 'Delete'],
                'resizable': True,
                'suppressMenu': True,
                'cellStyle': {'textAlign': 'center'}
            }
            column_defs.append(col_def)
        
        return clean_df, column_defs
        
    except Exception as e:
        import traceback
        st.error(f"Error preparing data for grid: {str(e)}")
        st.error(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame(), []

# JavaScript code for the edit button
edit_button_js = """
function(params) {
    const button = document.createElement('button');
    button.innerHTML = '✏️ Edit';
    button.style.cursor = 'pointer';
    button.style.padding = '4px 8px';
    button.style.border = '1px solid #ccc';
    button.style.borderRadius = '4px';
    button.style.backgroundColor = '#f8f9fa';
    button.style.color = '#333';
    
    button.onclick = (e) => {
        e.stopPropagation();
        const rowData = params.node.data;
        const rowId = rowData.ID !== undefined ? rowData.ID : rowData.id;
        if (rowId !== undefined) {
            document.body.dispatchEvent(
                new CustomEvent('button_click', { 
                    detail: { 
                        action: 'edit',
                        id: rowId
                    }
                })
            );
        }
    };
    
    return button;
}
"""

# JavaScript code for the delete button
delete_button_js = """
function(params) {
    const button = document.createElement('button');
    button.innerHTML = '🗑️ Delete';
    button.style.cursor = 'pointer';
    button.style.padding = '4px 8px';
    button.style.border = '1px solid #ffebee';
    button.style.borderRadius = '4px';
    button.style.backgroundColor = '#ffebee';
    button.style.color = '#c62828';
    
    button.onclick = (e) => {
        e.stopPropagation();
        if (confirm('Are you sure you want to delete this prediction?')) {
            const rowData = params.node.data;
            const rowId = rowData.ID !== undefined ? rowData.ID : rowData.id;
            if (rowId !== undefined) {
                document.body.dispatchEvent(
                    new CustomEvent('button_click', { 
                        detail: { 
                            action: 'delete',
                            id: rowId
                        }
                    })
                );
            }
        }
    };
    
    return button;
}
"""

def display_predictions_with_buttons(predictions_df):
    """
    Display predictions dataframe with edit and delete buttons directly in the table
    
    Args:
        predictions_df: Pandas DataFrame with predictions data
    
    Returns:
        Dictionary with action and prediction_id if a button was clicked
    """
    # Create a copy of the dataframe for display
    display_df = predictions_df.copy()
    
    # Ensure ID column is available for row identification
    if 'ID' not in display_df.columns and 'id' in display_df.columns:
        display_df = display_df.rename(columns={'id': 'ID'})
    
    # Define custom cell renderers for edit and delete buttons
    button_style = """
    function(params) {
        const button = document.createElement('button');
        button.innerHTML = params.value;
        button.style.cssText = `
            width: 100%;
            height: 100%;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        `;
        
        if (params.value === 'Edit') {
            button.innerHTML = '✏️ ' + button.innerHTML;
            button.style.backgroundColor = '#4CAF50';
            button.style.color = 'white';
            button.onmouseover = function() {
                this.style.backgroundColor = '#45a049';
                this.style.transform = 'translateY(-1px)';
                this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            };
        } else {
            button.innerHTML = '🗑️ ' + button.innerHTML;
            button.style.backgroundColor = '#f44336';
            button.style.color = 'white';
            button.onmouseover = function() {
                this.style.backgroundColor = '#d32f2f';
                this.style.transform = 'translateY(-1px)';
                this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            };
        }
        
        button.onmouseout = function() {
            this.style.transform = '';
            this.style.boxShadow = '';
            if (params.value === 'Edit') {
                this.style.backgroundColor = '#4CAF50';
            } else {
                this.style.backgroundColor = '#f44336';
            }
        };
        
        button.onclick = (e) => {
            e.stopPropagation();
            const rowData = params.node.data;
            // Handle both 'ID' and 'id' column names for compatibility
            const rowId = rowData.ID !== undefined ? rowData.ID : rowData.id;
            if (rowId !== undefined) {
                document.body.dispatchEvent(
                    new CustomEvent('button_click', { 
                        detail: { 
                            action: params.value.toLowerCase(),
                            id: rowId
                        }
                    })
                );
            } else {
                console.error('Could not find ID in row data:', rowData);
            }
        };
        
        return button;
    }
    """
    
    # Add button columns to the dataframe
    display_df['Edit'] = 'Edit'
    display_df['Delete'] = 'Delete'
    
    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(
        min_column_width=100,
        resizable=True,
        filterable=True,
        sortable=True
    )
    
    # Configure button columns
    gb.configure_column('Edit', 
                       header_name='',
                       cellRenderer=JsCode(button_style),
                       width=90,
                       pinned='left',
                       suppressMenu=True,
                       sortable=False,
                       filterable=False)
    
    gb.configure_column('Delete',
                        header_name='',
                        cellRenderer=JsCode(button_style),
                        width=90,
                        pinned='left',
                        suppressMenu=True,
                        sortable=False,
                        filterable=False)
    
    # Hide ID column from display but keep it in the data
    if 'ID' in display_df.columns:
        gb.configure_column('ID', hide=True)
    
    # Configure grid options
    grid_options = gb.build()
    
    # Set grid display options
    grid_options.update({
        'domLayout': 'autoHeight',
        'animateRows': True,
        'rowHeight': 50
    })
    
    # Add custom CSS for the grid
    st.markdown("""
    <style>
        .ag-theme-streamlit {
            --ag-border-radius: 8px;
            --ag-border-color: #e0e0e0;
            --ag-row-hover-color: #f5f5f5;
            --ag-header-background-color: #f8f9fa;
            --ag-odd-row-background-color: #ffffff;
            --ag-header-foreground-color: #495057;
            --ag-font-size: 14px;
            --ag-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }
        .ag-header-cell {
            font-weight: 600 !important;
        }
        .ag-cell {
            display: flex;
            align-items: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Create a container for the grid with a key based on the current time
    container = st.container()
    
    # Display the AgGrid with buttons
    with container:
        # JavaScript for handling button clicks
        button_clicked = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Function to handle button clicks
            function handleButtonClick(event) {
                try {
                    const button = event.target.closest('.action-button');
                    if (!button) return;
                    
                    const action = button.getAttribute('data-action');
                    const rowId = button.closest('tr').getAttribute('row-id');
                    
                    if (!action || !rowId) {
                        console.error('Missing action or rowId');
                        return;
                    }
                    
                    // Send message to Streamlit
                    const message = {
                        'action': action,
                        'row_id': rowId,
                        'timestamp': new Date().getTime()
                    };
                    
                    window.parent.postMessage({
                        'isStreamlitMessage': true,
                        'type': 'streamlit:component_message',
                        'api': 'component_1',
                        'args': JSON.stringify(message)
                    }, '*');
                    
                    // Store in session storage as fallback
                    sessionStorage.setItem('last_button_click', JSON.stringify(message));
                    
                } catch (error) {
                    console.error('Error handling button click:', error);
                }
            }
            
            // Add event listeners to all action buttons
            function setupButtonListeners() {
                document.removeEventListener('click', handleButtonClick);
                document.addEventListener('click', handleButtonClick);
                
                // Also set up a mutation observer to handle dynamic content
                if (!window.gridObserver) {
                    window.gridObserver = new MutationObserver(function(mutations) {
                        setupButtonListeners();
                    });
                    
                    window.gridObserver.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                }
            }
            
            // Initial setup
            setupButtonListeners();
            
            // Also set up a periodic check to ensure buttons stay connected
            setInterval(setupButtonListeners, 1000);
        });
        </script>
        """
        
        # Create a clean copy of the DataFrame and prepare it for AgGrid
        display_df = display_df.copy()
        
        # Prepare data for AgGrid
        grid_data, column_defs = prepare_data_for_aggrid(display_df)
        
        # Initialize GridOptionsBuilder with the prepared data
        gb = GridOptionsBuilder.from_dataframe(
            grid_data,
            enableRowGroup=False,
            enableValue=False,
            enablePivot=False
        )
        
        # Configure default column properties
        gb.configure_default_column(
            filterable=True,
            sortable=True,
            resizable=True,
            editable=False,
            groupable=False,
            suppressMenu=True
        )
        
        # Configure action buttons if they exist in the DataFrame
        if 'Edit' in grid_data.columns:
            gb.configure_column('Edit', 
                             width=80, 
                             cellRenderer=JsCode(edit_button_js),
                             sortable=False, 
                             filter=False,
                             suppressMenu=True)
        
        if 'Delete' in grid_data.columns:
            gb.configure_column('Delete', 
                             width=90, 
                             cellRenderer=JsCode(delete_button_js),
                             sortable=False, 
                             filter=False,
                             suppressMenu=True)
        
        # Configure grid options
        gb.configure_grid_options(
            enableCellTextSelection=True,
            ensureDomOrder=True,
            suppressRowClickSelection=True,
            suppressColumnVirtualisation=True,
            suppressRowVirtualisation=True,
            suppressDragLeaveHidesColumns=True
        )
        
        # Get the grid options
        grid_options = gb.build()
        
        try:
            # Ensure we have valid data
            if grid_data is None or grid_data.empty:
                st.warning("No data available to display.")
                return {
                    'data': pd.DataFrame(),
                    'selected_rows': [],
                    'action': '',
                    'row_id': ''
                }
            
            # Create a copy of the data to avoid modifying the original
            display_data = grid_data.copy()
            
            # Initialize GridOptionsBuilder with the data
            gb = GridOptionsBuilder.from_dataframe(display_data)
            
            # Configure default column properties
            gb.configure_default_column(
                filterable=True,
                sortable=True,
                resizable=True,
                editable=False,
                groupable=False,
                suppressMenu=True
            )
            
            # Configure action buttons if they exist in the DataFrame
            if 'Edit' in display_data.columns:
                gb.configure_column('Edit', 
                                 width=80, 
                                 cellRenderer=JsCode(edit_button_js),
                                 sortable=False, 
                                 filter=False,
                                 suppressMenu=True)
            
            if 'Delete' in display_data.columns:
                gb.configure_column('Delete', 
                                 width=90, 
                                 cellRenderer=JsCode(delete_button_js),
                                 sortable=False, 
                                 filter=False,
                                 suppressMenu=True)
            
            # Configure grid options
            gb.configure_grid_options(
                enableCellTextSelection=True,
                ensureDomOrder=True,
                suppressRowClickSelection=True,
                suppressColumnVirtualisation=True,
                suppressRowVirtualisation=True,
                suppressDragLeaveHidesColumns=True
            )
            
            # Get the grid options
            grid_options = gb.build()
            
            # Convert DataFrame to a format that AgGrid can handle
            # This helps avoid issues with pandas versions and data types
            grid_data = display_data.copy()
            
            # Ensure all values are JSON serializable
            for col in grid_data.columns:
                if pd.api.types.is_object_dtype(grid_data[col]):
                    grid_data[col] = grid_data[col].astype(str)
                elif pd.api.types.is_numeric_dtype(grid_data[col]):
                    # Convert numeric columns to string, handling NaN/None values
                    grid_data[col] = grid_data[col].astype('object').fillna('').astype(str)
                else:
                    grid_data[col] = grid_data[col].astype(str)
            
            # Convert to dictionary records for better compatibility
            grid_records = grid_data.to_dict('records')
            
            # Display the AgGrid component with simplified options
            grid_response = AgGrid(
                pd.DataFrame(grid_records),  # Convert back to DataFrame to ensure proper handling
                grid_options=grid_options,
                update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.VALUE_CHANGED,
                fit_columns_on_grid_load=True,
                theme='streamlit',
                height=min(600, (len(display_data) + 1) * 50 + 50) if len(display_data) > 0 else 200,
                width='100%',
                reload_data=False,
                allow_unsafe_jscode=True,
                custom_css={
                    ".ag-header-cell-label": {"justifyContent": "center"},
                    ".ag-cell": {"display": "flex", "alignItems": "center", "justifyContent": "center"},
                    ".ag-row-odd": {"backgroundColor": "#f9f9f9"},
                    ".ag-row-hover": {"backgroundColor": "#f0f0f0 !important"},
                    ".ag-center-cols-viewport": {"overflow-x": "auto"}
                },
                columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                enable_enterprise_modules=False,
                data_return_mode='FILTERED_AND_SORTED',
                try_to_convert_back_to_data_frame=True,  # Let AgGrid handle the conversion
                key='predictions_grid',
                suppressColumnVirtualisation=True,
                suppressRowVirtualisation=True,
                update_data_on_first_render=True,
                allow_unsafe_html=True,
                allow_unsafe_jscode=True
            )
            
            # Add the JavaScript for handling button clicks
            st.components.v1.html(button_clicked, height=0)
            
            return {
                'data': grid_response['data'],
                'selected_rows': grid_response['selected_rows'],
                'action': st.session_state.get('last_button_clicked', {}).get('action', ''),
                'row_id': st.session_state.get('last_button_clicked', {}).get('row_id', '')
            }
            
        except Exception as e:
            st.error(f"Error displaying predictions table: {str(e)}")
            st.error("Please try refreshing the page or contact support if the issue persists.")
            
            # Return a properly formatted response even on error
            return {
                'data': pd.DataFrame(),
                'selected_rows': [],
                'action': '',
                'row_id': ''
            }
        
        # Add the JavaScript for handling button clicks
        st.components.v1.html(button_clicked, height=0)
        
        # Check if a button was clicked
        button_click_data = None
        try:
            button_click_data = st.session_state.get('button_click_data')
            if button_click_data:
                # Parse the JSON data
                data = json.loads(button_click_data)
                # Clear the state to prevent multiple triggers
                st.session_state.pop('button_click_data', None)
                
                # Return the action and ID
                return {
                    "action": data["action"].lower(),
                    "prediction_id": data["id"]
                }
        except Exception as e:
            st.error(f"Error processing button click: {str(e)}")
        
        # Return default response if no button was clicked
        return {"action": None, "prediction_id": None}
