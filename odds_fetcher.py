

import logging
from supabase_db import SupabaseDB
from unidecode import unidecode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OddsFetcher:
    def __init__(self):
        """Initialize the OddsFetcher with a Supabase connection"""
        self.supabase = SupabaseDB().supabase
        logger.info("OddsFetcher initialized with Supabase connection")
    
    def normalize_team_name(self, team_name):
        """Normalize team name for comparison by removing accents, standardizing prefixes, and converting to lowercase"""
        if not team_name:
            return ""
            
        # Standardize AL/El prefixes (common in Arabic names)
        name = team_name
        prefixes = ['IF ', 'FC ', 'CD ', 'CA ', 'IFK ', 'UMF ', 'AL ', 'Al ', 'al ', 'EL ', 'El ', 'el ']
        
        # Special handling for teams that should keep their AL prefix
        keep_al_prefix = ['al-ahli', 'al-ittihad', 'al-hilal', 'al-nassr', 'al-fateh', 
                         'al-raed', 'al-taawon', 'al-faisaly', 'al-adalah', 'al-hazm',
                         'al-batin', 'al-fayha', 'al-tai', 'al-khaleej', 'al-ettifaq',
                         'al-raed', 'al-quadisiya', 'al-orubah', 'al-shabab', 'al-ittifaq']
        
        # Convert to lowercase for comparison
        name_lower = name.lower()
        
        # Check if we should keep the AL prefix
        should_keep_al = any(team in name_lower for team in keep_al_prefix)
        
        # Process prefixes
        for prefix in prefixes:
            if name.startswith(prefix):
                # Only remove the prefix if we shouldn't keep the AL
                if not (prefix.lower().strip() == 'al' and should_keep_al):
                    name = name[len(prefix):].strip()
        
        # Remove common suffixes that might cause mismatches
        suffixes = [' FC', ' IF', ' AIF', ' United', ' City', ' CF', ' UBK', ' Jrs.', ' SC', ' AFC']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Remove any remaining non-alphanumeric characters except spaces and hyphens
        import re
        name = re.sub(r'[^\w\s-]', '', name)
        
        # Standardize AL prefix
        if should_keep_al and not name.lower().startswith('al-'):
            name = f"Al-{name}"
        
        # Remove accents and convert to lowercase
        normalized = unidecode(name).strip()
        
        # Log the normalization for debugging
        if name != team_name:
            logger.info(f"Normalized team name: '{team_name}' -> '{name}' -> '{normalized}'")
        else:
            logger.info(f"Normalized team name: '{team_name}' -> '{normalized}'")
            
        return normalized.lower()
    
    def get_odds_from_db(self, home_team, away_team, league_name=None):
        """
        Fetch odds from the football_odds table for a specific match
        
        Args:
            home_team (str): Home team name
            away_team (str): Away team name
            league_name (str, optional): League name to further filter results
            
        Returns:
            dict: Dictionary containing odds data if found, None otherwise
        """
        try:
            # Team name mappings for all leagues in the database
            team_mappings = {
                # Slovakia Super Liga teams
                'FK Košice': 'MFK Kosice',
                'Podbrezová': 'FK ZP Podbrezova',
                'DAC': 'DAC Dunajska Streda',
                'Zemplín Michalovce': 'MFK Zemplin Michalovce',
                'Slovan Bratislava': 'Slovan Bratislava',
                'Spartak Trnava': 'Spartak Trnava',
                'Žilina': 'MSK Zilina',
                'Trenčín': 'AS Trencin',
                'Ružomberok': 'MFK Ruzomberok',
                'Zlaté Moravce': 'FC ViOn Zlate Moravce',
                'Skalica': 'MFK Skalica',
                'Dukla B.B.': 'FK Dukla Banska Bystrica',
                
                # Saudi Pro League teams
                'Al Quadisiya': 'Al Quadisiya',
                'Al Orubah': 'Al Orubah',
                'Al Taawon': 'Al Taawon',
                'Al Riyadh': 'Al Riyadh',
                'Al Shabab': 'Al Shabab',
                'Al Ittihad': 'Al Ittihad',
                
                # Swedish teams
                'Mjällby': 'Mjallby AIF',
                'Brommapojkarna': 'IF Brommapojkarna',
                'Sirius': 'Sirius',
                'Norrköping': 'IFK Norrkoping',
                'Degerfors': 'Degerfors IF',
                'IFK Göteborg': 'IFK Goteborg',
                'Elfsborg': 'IF Elfsborg',
                'Djurgården': 'Djurgardens IF',
                
                # Danish teams
                'Brøndby': 'Bröndby',
                'Midtjylland': 'Midtjylland',
                
                # English teams
                'Brighton': 'Brighton',
                'Liverpool': 'Liverpool',
                'Crystal Palace': 'Crystal Palace',
                'Wolves': 'Wolves',
                'Manchester City': 'Man City',
                'Man City': 'Man City',
                'Bournemouth': 'Bournemouth',
                
                # Spanish teams
                'Córdoba': 'Cordoba CF',
                'Mirandés': 'CD Mirandes',
                
                # Icelandic teams
                'Breiðablik': 'Breidablik UBK',
                'Valur': 'Valur Reykjavik',
                'ÍA': 'IA Akranes',
                'FH': 'FH Hafnarfjordur',
                'Stjarnan': 'UMF Stjarnan',
                'Víkingur': 'Vikingur Reykjavik',
                
                # Polish teams
                'Widzew Łódź': 'Widzew Lodz',
                'Puszcza': 'Puszcza Niepolomice',
                
                # Romanian teams
                'Rapid București': 'Rapid Bucuresti',
                'CFR Cluj': 'CFR Cluj',
                
                # Argentinian teams
                'Argentinos Juniors': 'Argentinos Jrs.',
                'San Lorenzo': 'CA San Lorenzo',
                'Boca Juniors': 'Boca Juniors',
                'Independiente': 'CA Independiente',
                'River Plate': 'CA River Plate',
                'Platense': 'CA Platense',
                'ARG': 'Argentinos Jrs.',
                'SAN': 'CA San Lorenzo'
            }
            
            # League name mappings
            league_mappings = {
                'England - Premier League': 'Premier League, England',
                'Premier League': 'Premier League, England',
                'Spain - LaLiga 2': 'LaLiga 2, Spain',
                'LaLiga 2': 'LaLiga 2, Spain',
                'Denmark - Superliga': 'Superliga, Denmark',
                'Superliga': 'Superliga, Denmark',
                'Sweden - Allsvenskan': 'Allsvenskan, Sweden',
                'Allsvenskan': 'Allsvenskan, Sweden',
                'Iceland - Besta deild': 'Besta deild, Iceland',
                'Besta deild': 'Besta deild, Iceland',
                'Poland - Ekstraklasa': 'Ekstraklasa, Poland',
                'Ekstraklasa': 'Ekstraklasa, Poland',
                'Romania - Liga I': 'Liga I, Romania',
                'Liga I': 'Liga I, Romania',
                'Argentina - Liga Profesional': 'Liga Profesional, Argentina',
                'Liga Profesional': 'Liga Profesional, Argentina',
                'Argentine football league - Primera Nacional': 'Liga Profesional, Argentina',
                'Argentine football league': 'Liga Profesional, Argentina',
                'Primera Nacional': 'Liga Profesional, Argentina',
                'Argentina': 'Liga Profesional, Argentina',
                
                # Saudi Pro League
                'Saudi Arabia - Pro League': 'Saudi Pro League, Saudi Arabia',
                'Saudi Pro League': 'Saudi Pro League, Saudi Arabia',
                'Saudi Professional League': 'Saudi Pro League, Saudi Arabia',
                'Saudi': 'Saudi Pro League, Saudi Arabia',
                
                # Slovakia Super Liga
                'Slovakia - Super Liga': 'Fortuna Liga, Slovakia',
                'Slovak Super Liga': 'Fortuna Liga, Slovakia',
                'Slovak First League': 'Fortuna Liga, Slovakia',
                'Fortuna Liga': 'Fortuna Liga, Slovakia',
                'Slovakia': 'Fortuna Liga, Slovakia'
            }
            
            # Apply mappings if available
            mapped_home = team_mappings.get(home_team, home_team)
            mapped_away = team_mappings.get(away_team, away_team)
            mapped_league = league_mappings.get(league_name, league_name) if league_name else None
            
            # Build the query
            query = self.supabase.table('football_odds')
            
            # Fetch all records
            result = query.select('*').execute()
            
            if not result.data:
                return None
            
            # Direct match first - exact match for team names and league
            for odds in result.data:
                db_home = odds.get('team1', '')
                db_away = odds.get('team2', '')
                db_league = odds.get('league_name', '')
                
                # Check for exact match with mapped names
                if (db_home == mapped_home and db_away == mapped_away and 
                    (not mapped_league or db_league == mapped_league)):
                    return {
                        'home_odds': float(odds.get('home_odds', 0)),
                        'draw_odds': float(odds.get('draw_odds', 0)),
                        'away_odds': float(odds.get('away_odds', 0)),
                        'over25_odds': float(odds.get('over_odds', 0)),
                        'under25_odds': float(odds.get('under_odds', 0)),
                        'btts_yes_odds': float(odds.get('btts_yes', 0)),
                        'btts_no_odds': float(odds.get('btts_no', 0)),
                        'source': 'supabase'
                    }
            
            # If no exact match, try normalized match
            normalized_home = self.normalize_team_name(mapped_home)
            normalized_away = self.normalize_team_name(mapped_away)
            normalized_league = self.normalize_team_name(mapped_league) if mapped_league else None
            
            for odds in result.data:
                db_home = self.normalize_team_name(odds.get('team1', ''))
                db_away = self.normalize_team_name(odds.get('team2', ''))
                db_league = self.normalize_team_name(odds.get('league_name', ''))
                
                # Check for normalized match
                home_match = db_home == normalized_home or normalized_home in db_home or db_home in normalized_home
                away_match = db_away == normalized_away or normalized_away in db_away or db_away in normalized_away
                
                # Check if league matches
                league_match = True
                if normalized_league and db_league:
                    # Special case for Argentine league
                    if ('argentina' in normalized_league or 'argentine' in normalized_league) and \
                       ('argentina' in db_league or 'profesional' in db_league):
                        league_match = True
                    # Extract country names for comparison
                    elif ',' in db_league:
                        db_country = db_league.split(',')[1].strip().lower() if len(db_league.split(',')) > 1 else ''
                        db_league_name = db_league.split(',')[0].strip().lower()
                        
                        if ' - ' in normalized_league:
                            country = normalized_league.split(' - ')[0].strip().lower()
                            league = normalized_league.split(' - ')[1].strip().lower()
                            league_match = (country in db_country or db_country in country) and \
                                          (league in db_league_name or db_league_name in league)
                        else:
                            # Check if any part of the league name matches
                            words_in_normalized = set(normalized_league.split())
                            words_in_db = set(db_league.split())
                            common_words = words_in_normalized.intersection(words_in_db)
                            if len(common_words) > 0:
                                league_match = True
                            else:
                                league_match = normalized_league in db_league or db_league in normalized_league
                    else:
                        # Check if any part of the league name matches
                        words_in_normalized = set(normalized_league.split())
                        words_in_db = set(db_league.split())
                        common_words = words_in_normalized.intersection(words_in_db)
                        if len(common_words) > 0:
                            league_match = True
                        else:
                            league_match = normalized_league in db_league or db_league in normalized_league
                
                if home_match and away_match and league_match:
                    return {
                        'home_odds': float(odds.get('home_odds', 0)),
                        'draw_odds': float(odds.get('draw_odds', 0)),
                        'away_odds': float(odds.get('away_odds', 0)),
                        'over25_odds': float(odds.get('over_odds', 0)),
                        'under25_odds': float(odds.get('under_odds', 0)),
                        'btts_yes_odds': float(odds.get('btts_yes', 0)),
                        'btts_no_odds': float(odds.get('btts_no', 0)),
                        'source': 'supabase'
                    }
            
            logger.info(f"No matching odds found for {home_team} vs {away_team}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching odds from database: {str(e)}")
            return None
    
    def get_leagues_with_odds(self):
        """
        Get a list of leagues that have odds data in the database
        
        Returns:
            list: List of league names with odds data
        """
        try:
            result = self.supabase.table('football_odds').select('league_name').execute()
            
            if not result.data:
                return []
            
            # Extract unique league names
            leagues = set()
            for odds in result.data:
                league = odds.get('league_name')
                if league:
                    leagues.add(league)
            
            return list(leagues)
            
        except Exception as e:
            logger.error(f"Error fetching leagues with odds: {str(e)}")
            return []
    
    def convert_odds_to_probabilities(self, odds_data):
        """
        Convert odds to probabilities
        
        Args:
            odds_data (dict): Dictionary containing odds data
            
        Returns:
            dict: Dictionary containing probabilities
        """
        if not odds_data:
            return None
        
        try:
            # Extract odds
            home_odds = odds_data.get('home_odds', 0)
            draw_odds = odds_data.get('draw_odds', 0)
            away_odds = odds_data.get('away_odds', 0)
            
            # Ensure odds are valid
            if home_odds <= 1 or draw_odds <= 1 or away_odds <= 1:
                logger.warning("Invalid odds values")
                return None
            
            # Convert to raw probabilities
            home_prob = 1 / home_odds
            draw_prob = 1 / draw_odds
            away_prob = 1 / away_odds
            
            # Calculate the overround (margin)
            total_prob = home_prob + draw_prob + away_prob
            
            # Normalize probabilities to remove the margin
            if total_prob > 0:
                home_prob = home_prob / total_prob
                draw_prob = draw_prob / total_prob
                away_prob = away_prob / total_prob
            
            return {
                'home_prob': home_prob,
                'draw_prob': draw_prob,
                'away_prob': away_prob,
                'source': 'supabase'
            }
            
        except Exception as e:
            logger.error(f"Error converting odds to probabilities: {str(e)}")
            return None


# Simple test function to verify the module works
def test_odds_fetcher():
    fetcher = OddsFetcher()
    
    # Test getting odds for a match
    odds = fetcher.get_odds_from_db("Brighton", "Liverpool")
    print(f"Odds for Brighton vs Liverpool: {odds}")
    
    # Test getting leagues with odds
    leagues = fetcher.get_leagues_with_odds()
    print(f"Leagues with odds: {leagues}")
    
    # Test converting odds to probabilities
    if odds:
        probs = fetcher.convert_odds_to_probabilities(odds)
        print(f"Probabilities: {probs}")

if __name__ == "__main__":
    test_odds_fetcher()
