# history.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from football_api import get_match_by_teams, get_match_result
from session_state import init_session_state, check_login_state
from match_analyzer import MatchAnalyzer
import logging

class PredictionHistory:
    def __init__(self):
        """Initialize the database connection and create tables if they don't exist."""
        self.db_path = 'predictions.db'
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        
        # Create predictions table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                predicted_outcome TEXT,
                actual_outcome TEXT,
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                confidence REAL,
                bet_amount REAL,
                profit_loss REAL,
                prediction_type TEXT,
                status TEXT,
                match_date TEXT,
                match_id TEXT,
                home_score INTEGER,
                away_score INTEGER
            )
        ''')
        
        # Add new columns if they don't exist
        try:
            cursor.execute('ALTER TABLE predictions ADD COLUMN home_score INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute('ALTER TABLE predictions ADD COLUMN away_score INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        connection.commit()
        connection.close()

    def init_database(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create predictions table with all necessary fields
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                league TEXT,
                home_team TEXT,
                away_team TEXT,
                predicted_outcome TEXT,
                actual_outcome TEXT,
                home_odds REAL,
                draw_odds REAL,
                away_odds REAL,
                confidence REAL,
                bet_amount REAL,
                profit_loss REAL,
                prediction_type TEXT,
                status TEXT,
                match_date TEXT,
                match_id TEXT,
                home_score INTEGER,
                away_score INTEGER
            )
        ''')
        
        # Convert existing confidence values to REAL if needed
        try:
            c.execute('SELECT confidence FROM predictions LIMIT 1')
            sample = c.fetchone()
            if sample and isinstance(sample[0], bytes):
                # Create a temporary table
                c.execute('''
                    CREATE TABLE temp_predictions AS 
                    SELECT id, date, league, home_team, away_team, 
                           predicted_outcome, actual_outcome, home_odds, 
                           draw_odds, away_odds,
                           CAST((SELECT CAST(confidence AS REAL)) AS REAL) as confidence,
                           bet_amount, profit_loss, prediction_type, 
                           status, match_date, match_id, NULL as home_score, NULL as away_score
                    FROM predictions
                ''')
                
                # Drop the original table
                c.execute('DROP TABLE predictions')
                
                # Rename temp table to original
                c.execute('ALTER TABLE temp_predictions RENAME TO predictions')
        except:
            pass
        
        conn.commit()
        conn.close()

    def add_prediction(self, prediction_data):
        """Add a new prediction to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Ensure confidence is a float
            confidence = float(prediction_data.get('confidence', 0.0))
            match_id = str(prediction_data.get('match_id', ''))
            
            # Insert prediction
            cursor.execute("""
                INSERT INTO predictions (
                    date, league, home_team, away_team,
                    predicted_outcome, actual_outcome,
                    home_odds, draw_odds, away_odds,
                    confidence, bet_amount, profit_loss,
                    status, match_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction_data['date'],
                prediction_data['league'],
                prediction_data['home_team'],
                prediction_data['away_team'],
                prediction_data['predicted_outcome'],
                None,  # actual_outcome starts as None
                float(prediction_data['home_odds']),
                float(prediction_data['draw_odds']),
                float(prediction_data['away_odds']),
                confidence,
                float(prediction_data['bet_amount']),
                0.0,  # profit_loss starts at 0
                'Pending',  # status starts as Pending
                match_id
            ))
            
            conn.commit()
            conn.close()
            logging.info(f"Successfully added prediction for {prediction_data['home_team']} vs {prediction_data['away_team']} with match_id: {match_id} and confidence: {confidence}")
            return True
            
        except Exception as e:
            logging.error(f"Error adding prediction: {str(e)}")
            return False

    def update_prediction_result(self, prediction_id, actual_outcome, profit_loss):
        """Update prediction with actual result and profit/loss"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE predictions 
                SET actual_outcome = ?, 
                    profit_loss = ?,
                    status = 'Completed'
                WHERE id = ?
            """, (actual_outcome, profit_loss, prediction_id))
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating prediction result: {str(e)}")
            conn.rollback()
            
        finally:
            conn.close()

    def get_predictions(self, start_date=None, end_date=None, status=None, confidence_level=None, league=None):
        """Get predictions with optional filters"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                id, date, league, home_team, away_team, 
                predicted_outcome, actual_outcome, 
                home_odds, draw_odds, away_odds,
                confidence,
                bet_amount, profit_loss,
                status, match_id, home_score, away_score
            FROM predictions WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if status:
            query += " AND status = ?"
            params.append(status)
        if confidence_level:
            if confidence_level == "High":
                query += " AND confidence >= 70"
            elif confidence_level == "Medium":
                query += " AND confidence >= 50 AND confidence < 70"
            elif confidence_level == "Low":
                query += " AND confidence < 50"
        if league and league != "All":
            query += " AND league = ?"
            params.append(league)
            
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df

    def calculate_statistics(self, confidence_level=None, league=None):
        """Calculate prediction statistics with optional confidence level and league filter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN predicted_outcome = actual_outcome AND actual_outcome IS NOT NULL THEN 1 ELSE 0 END) as correct,
                   SUM(profit_loss) as total_profit,
                   COUNT(CASE WHEN actual_outcome IS NULL THEN 1 END) as pending
            FROM predictions
            WHERE 1=1
        """
        params = []
        
        if confidence_level:
            if confidence_level == "High":
                query += " AND confidence >= 70"
            elif confidence_level == "Medium":
                query += " AND confidence >= 50 AND confidence < 70"
            elif confidence_level == "Low":
                query += " AND confidence < 50"
        
        if league and league != "All":
            query += " AND league = ?"
            params.append(league)
            
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        total = result[0] or 0
        correct = result[1] or 0
        total_profit = result[2] or 0
        pending_count = result[3] or 0
        
        success_rate = (correct / (total - pending_count) * 100) if total - pending_count > 0 else 0
        roi = (total_profit / total * 100) if total > 0 else 0
        
        conn.close()
        
        return [total, correct, success_rate, total_profit, roi], pending_count

    def update_match_results(self, match_id, result):
        """Update match results in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # First get the match details
            cursor.execute("""
                SELECT predicted_outcome, home_odds, draw_odds, away_odds
                FROM predictions 
                WHERE match_id = ?
            """, (match_id,))
            match_data = cursor.fetchone()
            
            if not match_data:
                print(f"No prediction found for match {match_id}")
                return
                
            predicted_outcome, home_odds, draw_odds, away_odds = match_data
            
            # Parse the result
            if isinstance(result, dict):
                home_score = result.get('home_score')
                away_score = result.get('away_score')
                status = result.get('status', 'Completed')
            else:
                home_score = result
                away_score = None
                status = 'Completed'
            
            # Determine actual outcome
            if home_score is not None and away_score is not None:
                if home_score > away_score:
                    actual_outcome = 'HOME'
                elif away_score > home_score:
                    actual_outcome = 'AWAY'
                else:
                    actual_outcome = 'DRAW'
                    
                # Calculate profit/loss using $1 bet amount
                if all([home_odds, draw_odds, away_odds]):  # Only if we have odds
                    odds = {
                        'home_odds': float(home_odds),
                        'draw_odds': float(draw_odds),
                        'away_odds': float(away_odds)
                    }
                    
                    # Get the odds for the predicted outcome
                    bet_odds = odds.get(f"{predicted_outcome.lower()}_odds")
                    
                    if predicted_outcome == actual_outcome:
                        # Won: Get the profit (odds - 1)
                        profit_loss = round(bet_odds - 1.0, 2)
                    else:
                        # Lost: Lose the $1 bet
                        profit_loss = -1.0
                else:
                    profit_loss = None
            else:
                actual_outcome = None
                profit_loss = None
            
            # Update the database
            cursor.execute('''
                UPDATE predictions
                SET status = ?,
                    home_score = ?,
                    away_score = ?,
                    actual_outcome = ?,
                    profit_loss = ?
                WHERE match_id = ?
            ''', (status, home_score, away_score, actual_outcome, profit_loss, match_id))
            
            conn.commit()
            print(f"Updated match {match_id} with status {status}, scores {home_score}-{away_score}, outcome {actual_outcome}, profit/loss {profit_loss}")
            
        except Exception as e:
            print(f"Error updating match {match_id}: {str(e)}")
            conn.rollback()
            
        finally:
            if conn:
                conn.close()

    def update_match_results_all(self):
        """Update completed match results using match_analyzer"""
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        analyzer = MatchAnalyzer("633379bdd5c4c3eb26919d8570866801e1c07f399197ba8c5311446b8ea77a49")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get pending predictions
        c.execute("""
            SELECT * FROM predictions 
            WHERE status IN ('Pending', 'pending') 
            AND match_id IS NOT NULL
        """)
        pending_predictions = c.fetchall()
        logger.info(f"Found {len(pending_predictions)} pending predictions")
        
        for pred in pending_predictions:
            try:
                pred_id = pred[0]  # prediction id
                match_id = pred[16]  # match_id
                if not match_id:
                    logger.warning(f"Skipping prediction {pred_id}: No match_id")
                    continue
                    
                logger.info(f"Processing match {match_id} for prediction {pred_id}")
                
                # Get match data from analyzer
                match_data = analyzer.get_match_details(match_id)
                if not match_data:
                    logger.warning(f"No match data found for match {match_id}")
                    continue
                    
                # Get match result
                result = analyzer.analyze_match_result(match_data)
                if not result:
                    logger.warning(f"No result data for match {match_id}")
                    continue
                
                self.update_match_results(match_id, result)
                
            except Exception as e:
                logger.error(f"Error updating match result for prediction {pred_id if 'pred_id' in locals() else None}: {str(e)}", exc_info=True)
                continue
        
        conn.close()



def style_dataframe(df):
    """Style the predictions dataframe with colors and formatting"""
    
    def format_result(row):
        if row['Status'] == 'Pending':
            return '⏳ Pending'
        elif pd.isna(row['Actual Outcome']) or row['Actual Outcome'] == '':
            return '⏳ Pending'
        elif row['Prediction'] == row['Actual Outcome']:
            return '✅ Won'
        else:
            return '❌ Lost'
            
    def format_actual_outcome(row):
        if row['Status'] == 'Pending' or pd.isna(row['Actual Outcome']) or row['Actual Outcome'] == '':
            return '-'  # Show dash for pending matches
        return row['Actual Outcome']

    def format_profit_loss(row):
        if row['Status'] == 'Pending':
            return '-'
        try:
            profit = float(row['Profit/Loss'])
            if profit > 0:
                return f'+${profit:.2f}'
            elif profit < 0:
                return f'-${abs(profit):.2f}'
            return '$0.00'
        except (ValueError, TypeError):
            return '-'

    # Create a copy to avoid modifying the original
    display_df = df.copy()
    
    # Format the Result column
    display_df['Result'] = display_df.apply(format_result, axis=1)
    
    # Format the Actual Outcome column
    display_df['Actual Outcome'] = display_df.apply(format_actual_outcome, axis=1)
    
    # Format Profit/Loss
    display_df['Profit/Loss'] = display_df.apply(format_profit_loss, axis=1)
    
    # Apply styling
    def style_row(row):
        base_style = [
            'font-size: 14px',
            'font-weight: 400',
            'color: #333333',
            'padding: 12px 15px',
            'border-bottom: 1px solid #e0e0e0'
        ]
        
        if row['Status'] == 'Pending':
            return [';'.join(base_style + ['background-color: #f5f5f5'])] * len(row)
        elif pd.isna(row['Actual Outcome']) or row['Actual Outcome'] == '':
            return [';'.join(base_style + ['background-color: #f5f5f5'])] * len(row)
        elif row['Prediction'] == row['Actual Outcome']:
            return [';'.join(base_style + ['background-color: #e8f5e9'])] * len(row)  # Lighter green
        else:
            return [';'.join(base_style + ['background-color: #fce4ec'])] * len(row)  # Lighter red
    
    # Create the styled DataFrame
    styled_df = display_df.style.apply(style_row, axis=1)
    
    # Add table styles
    styled_df.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', '#f8f9fa'),
            ('color', '#333333'),
            ('font-weight', '600'),
            ('font-size', '14px'),
            ('text-align', 'left'),
            ('padding', '12px 15px'),
            ('border-bottom', '2px solid #dee2e6')
        ]},
        {'selector': 'td', 'props': [
            ('text-align', 'left'),
            ('white-space', 'nowrap'),
            ('min-width', '100px')
        ]},
        {'selector': 'table', 'props': [
            ('border-collapse', 'collapse'),
            ('width', '100%'),
            ('margin', '10px 0'),
            ('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif')
        ]},
        {'selector': 'tr:hover td', 'props': [
            ('background-color', 'rgba(0,0,0,0.05) !important')
        ]}
    ])
    
    return styled_df

def get_confidence_level(confidence):
    """Convert confidence value to display text"""
    try:
        # Handle None, NaN, and empty values
        if confidence is None or pd.isna(confidence) or confidence == "":
            return "Unknown"
            
        # Convert to float and handle string values
        conf_value = float(str(confidence).strip())
        
        # Categorize confidence
        if conf_value >= 70:
            return "High"
        elif conf_value >= 50:
            return "Medium"
        elif conf_value >= 0:
            return "Low"
        else:
            return "Unknown"
    except (ValueError, TypeError, AttributeError):
        return "Unknown"

def show_history_page():
    """Display prediction history page"""
    st.markdown("""
        <style>
        .stDataFrame {
            font-size: 14px;
            width: 100%;
        }
        .stDataFrame [data-testid="StyledDataFrameDataCell"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 12px 15px !important;
            color: #333333 !important;
        }
        .stDataFrame [data-testid="StyledDataFrameHeaderCell"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 12px 15px !important;
            background-color: #f8f9fa !important;
            color: #333333 !important;
            font-weight: 600 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    if not check_login_state():
        st.warning("Please log in to view prediction history.")
        return

    # Custom CSS for styling
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            background-color: #f8f9fa;
            padding: 20px;
        }
        
        /* Title styling */
        .title-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 30px 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .title {
            color: white;
            font-size: 2.2em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }
        
        /* Metrics styling */
        .metrics-container {
            width: 200px;
            margin-bottom: 20px;
        }
        
        .metric-box {
            background: white;
            padding: 8px 12px;
            border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            text-align: left;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .metric-label {
            color: #666;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0;
        }
        
        .metric-value {
            font-size: 0.9rem;
            font-weight: bold;
            color: #2c5282;
            margin: 0;
        }
        
        .positive-value {
            color: #48bb78;
        }
        
        .negative-value {
            color: #f56565;
        }

        @media (max-width: 768px) {
            .metrics-grid {
                flex-wrap: wrap;
            }
            .metric-box {
                min-width: calc(50% - 10px);
            }
        }
        
        /* Table styling */
        .dataframe {
            border-collapse: separate !important;
            border-spacing: 0;
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .dataframe th {
            background-color: #f8f9fa !important;
            color: #495057 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 15px !important;
            border-bottom: 2px solid #dee2e6 !important;
        }
        
        .dataframe td {
            padding: 12px 15px !important;
            border-bottom: 1px solid #e9ecef !important;
            color: #212529 !important;
            background-color: white !important;
        }
        
        .dataframe tr:hover td {
            background-color: #f8f9fa !important;
        }
        
        /* Status indicators */
        .status-pending {
            color: #6c757d;
            background-color: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        .status-win {
            color: #28a745;
            background-color: #e8f5e9;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        .status-loss {
            color: #dc3545;
            background-color: #fbe9e7;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 500;
        }
        
        /* Date filter styling */
        .date-filter {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        </style>
    """, unsafe_allow_html=True)

    # Display title with custom styling
    st.markdown("""
        <div class="title-container">
            <h1 class="title">Prediction History</h1>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        # Initialize PredictionHistory
        history = PredictionHistory()
        
        # Add date filter in sidebar with custom styling
        st.sidebar.markdown("""
            <div class="date-filter">
                <h2 style='color: #1e3c72; font-size: 1.2em; margin-bottom: 15px;'>Filters</h2>
            </div>
        """, unsafe_allow_html=True)
        
        # Get min and max dates from predictions
        all_predictions = history.get_predictions()
        if not all_predictions.empty:
            min_date = pd.to_datetime(all_predictions['date']).min()
            max_date = pd.to_datetime(all_predictions['date']).max()
            
            # Date range selector
            start_date = st.sidebar.date_input(
                "Start Date",
                min_date,
                min_value=min_date,
                max_value=max_date
            )
            
            end_date = st.sidebar.date_input(
                "End Date",
                max_date,
                min_value=start_date,
                max_value=max_date
            )

            # Add confidence level filter
            confidence_level = st.sidebar.selectbox(
                "Confidence Level",
                ["All", "High", "Medium", "Low"],
                help="Filter predictions by confidence level: High (≥70%), Medium (50-69%), Low (<50%)"
            )
            
            # Add league filter
            leagues = all_predictions['league'].unique().tolist()
            leagues.insert(0, "All")
            league = st.sidebar.selectbox(
                "League",
                leagues,
                index=0
            )
            
            # Get filtered predictions
            predictions = history.get_predictions(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                confidence_level=None if confidence_level == "All" else confidence_level,
                league=league
            )
            
            if not predictions.empty:
                # Update any pending predictions
                history.update_match_results_all()
                
                # Refresh predictions after update
                predictions = history.get_predictions(
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    confidence_level=None if confidence_level == "All" else confidence_level,
                    league=league
                )
                
                # Calculate statistics
                current_confidence = None if confidence_level == "All" else confidence_level
                current_league = None if league == "All" else league
                stats, pending_count = history.calculate_statistics(confidence_level=current_confidence, league=current_league)
                
                # Create metrics container
                st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
                
                # Display each metric
                metrics = [
                    {"label": "Total Predictions", "value": stats[0], "is_percentage": False, "is_currency": False},
                    {"label": "Correct Predictions", "value": stats[1], "is_percentage": False, "is_currency": False},
                    {"label": "Success Rate", "value": stats[2], "is_percentage": True, "is_currency": False},
                    {"label": "Total Profit", "value": stats[3], "is_currency": True, "is_percentage": False},
                    {"label": "ROI", "value": stats[4], "is_percentage": True, "is_currency": False},
                    {"label": "Pending Predictions", "value": pending_count, "is_percentage": False, "is_currency": False}
                ]
                
                for metric in metrics:
                    if metric.get("is_currency"):
                        formatted_value = f"£{metric['value']:.2f}"
                    elif metric.get("is_percentage"):
                        formatted_value = f"{metric['value']:.1f}%"
                    else:
                        formatted_value = str(metric['value'])
                    
                    value_class = ""
                    if metric.get("is_currency") or metric.get("is_percentage"):
                        try:
                            value = float(metric['value'])
                            value_class = " positive-value" if value > 0 else " negative-value" if value < 0 else ""
                        except (ValueError, TypeError):
                            value_class = ""
                    
                    st.markdown(f"""
                        <div class="metric-box">
                            <div class="metric-label">{metric['label']}</div>
                            <div class="metric-value{value_class}">{formatted_value}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Display predictions table
                if not predictions.empty:
                    st.markdown("""
                        <h2 style='color: #1e3c72; font-size: 1.5em; margin: 30px 0 20px;'>
                            Recent Predictions
                        </h2>
                    """, unsafe_allow_html=True)
                    
                    try:
                        # Convert confidence to numeric and create display version
                        predictions['confidence_num'] = pd.to_numeric(predictions['confidence'], errors='coerce')
                        predictions['Confidence'] = predictions['confidence_num'].apply(get_confidence_level)
                        
                        # Convert date to datetime
                        predictions['date'] = pd.to_datetime(predictions['date']).dt.strftime('%Y-%m-%d')
                        
                        # Create Result column
                        predictions['Result'] = predictions.apply(
                            lambda x: '✅ Won' if pd.notna(x['predicted_outcome']) and x['predicted_outcome'] == x['actual_outcome']
                            else '❌ Lost' if pd.notna(x['actual_outcome'])
                            else '⏳ Pending',
                            axis=1
                        )
                        
                        # Define display columns mapping
                        display_columns = {
                            'date': 'Date',
                            'league': 'League',
                            'home_team': 'Home Team',
                            'away_team': 'Away Team',
                            'predicted_outcome': 'Prediction',
                            'Confidence': 'Confidence',
                            'actual_outcome': 'Actual Outcome',
                            'Result': 'Result',
                            'profit_loss': 'Profit/Loss',
                            'status': 'Status'
                        }
                        
                        # Create final dataframe
                        final_df = predictions[list(display_columns.keys())].copy()
                        final_df = final_df.rename(columns=display_columns)
                        
                        # Apply styling
                        styled_df = style_dataframe(final_df)
                        
                        # Display the styled dataframe
                        st.dataframe(
                            styled_df,
                            use_container_width=True,
                            hide_index=True
                        )
                        
                    except Exception as e:
                        st.error(f"Error displaying predictions table: {str(e)}")
                        st.exception(e)
                else:
                    st.info("No predictions found for the selected date range.")
                
    except Exception as e:
        st.error(f"Error displaying predictions table: {str(e)}")
        st.exception(e)

    # Add Navigation JavaScript
    st.markdown("""
    <script>
        function handleLogout() {
            // Clear session state
            localStorage.clear();
            sessionStorage.clear();
            
            // Redirect to home page
            window.location.href = '/';
        }

        function navigateToHome() {
            window.location.href = '/';
        }

        function navigateToHistory() {
            window.location.href = '/?page=history';
        }
    </script>
    """, unsafe_allow_html=True)

    # Add navigation buttons
    def add_navigation_buttons():
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if st.button("🏠 Home", key="home"):
                st.query_params["page"] = "main"
                st.rerun()
                
        with col2:
            if st.button("📊 History", key="history"):
                st.query_params["page"] = "history"
                st.rerun()
                
        with col3:
            if st.button("🚪 Logout", key="logout"):
                st.session_state.logged_in = False
                st.query_params.clear()
                st.rerun()

    # Call the function to add navigation buttons
    add_navigation_buttons()

    # Add back button
    if st.button("Back to Predictions"):
        st.query_params["page"] = "main"
        st.rerun()
