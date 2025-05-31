# DinnerPlanner 🍽️

DinnerPlanner is an AI-powered meal planning assistant that helps you plan your weekly dinners and generate shopping lists. It features a modern web interface and intelligent conversation capabilities to understand your preferences and dietary requirements.

## Features

- 🤖 AI-powered conversational interface
- 📅 Weekly meal planning
- 🥗 Dietary preference support
- 📝 Automatic shopping list generation
- 🔄 Recipe scaling for different serving sizes
- 💬 Real-time chat interface
- 🌐 Web-based responsive UI

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs with Python
- **WebSocket**: Real-time bidirectional communication
- **OpenAI API**: GPT-powered conversation and recipe understanding
- **Python 3.12**: Latest Python version with modern async features
- **Uvicorn**: Lightning-fast ASGI server
- **Pydantic**: Data validation using Python type annotations

### Frontend
- **HTML5/CSS3**: Modern, semantic markup and styling
- **JavaScript**: Native WebSocket handling and UI interactions
- **Inter Font**: Modern typography
- **Responsive Design**: Mobile-first approach
- **CSS Grid/Flexbox**: Modern layout system

### DevOps
- **Railway**: Production deployment platform
- **Environment Management**: Python virtual environments
- **Git**: Version control
- **WSL2**: Windows Subsystem for Linux support

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dinner-planner.git
cd dinner-planner
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

5. Run the development server:
```bash
uvicorn app:app --reload
```

6. Open http://localhost:8000 in your browser

## Project Structure

```
dinner-planner/
├── app.py              # FastAPI application entry point
├── agent.py            # AI agent implementation
├── config.py           # Configuration management
├── static/             # Static files
│   └── index.html      # Web interface
├── tools/              # Helper modules
│   ├── recipe.py       # Recipe handling
│   ├── shopping_list.py# Shopping list generation
│   └── user_input.py   # User preference management
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Future Improvements

- [ ] Implement user accounts and saved preferences
- [ ] Implement grocery store integration
- [ ] Add meal plan history and recipe favoriting
- [ ] Create meal plan optimization based on nutritional goals
- [ ] Create mobile app and voice clients

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for providing the GPT API
- FastAPI team for the excellent framework
- Railway for hosting support 