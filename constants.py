class Constants():
    # Map constants
    COLORS = ['#CFC1A3', '#9E8959', '#5A0414', '#282220', '#58585B']

    # Scale constants
    SCALE_FACTOR = 100

    # HTML constants
    HTML_BASE = '''
        <div id="legend" style="position: fixed; 
            bottom: 20px; left: 20px; width: auto; height: auto; 
            border:2px solid grey; z-index:9999; font-size:14px;
            background-color:white;
            padding: 10px; overflow-y: auto;">
            <strong onclick="toggleVisibility('legend-content');" style="cursor: pointer;">TSP Path Route:</strong><br>
            <div id="legend-content" style="display: block;">
        '''
    
    HTML_END = '''
            </div>
        </div>
        <script>
        function toggleVisibility(id) {
            var e = document.getElementById(id);
            if(e.style.display == 'block')
                e.style.display = 'none';
            else
                e.style.display = 'block';
        }
        </script>
        '''
    
    # CSS constants
    CSS_TITLE_ABOVE_NAVBAR = '''
                <style>
                    [data-testid="stSidebarNav"]::before {
                        content: "Navigation";
                        margin-left: 20px;
                        margin-top: 20px;
                        font-size: 30px;
                        position: relative;
                        top: 100px;
                    }
                </style>
                '''