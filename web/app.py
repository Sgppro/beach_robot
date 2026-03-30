from flask import Flask, render_template, request

app = Flask(__name__)

# Starting coordinates for the dot (in pixels from the top-left corner)
current_x = 100
current_y = 100

@app.route('/', methods=['GET', 'POST'])
def index():
    global current_x, current_y
    
    # If the user clicked the "Update Location" button
    if request.method == 'POST':
        try:
            # Grab the new coordinates from the web form
            current_x = int(request.form.get('x_coord', current_x))
            current_y = int(request.form.get('y_coord', current_y))
        except ValueError:
            pass # Ignore invalid inputs and keep the old coordinates
            
    # Send the coordinates to the HTML page
    return render_template('index.html', x=current_x, y=current_y)

if __name__ == '__main__':
    # host='0.0.0.0' allows you to access this from other devices on your network
    app.run(debug=True, host='0.0.0.0', port=5000)
