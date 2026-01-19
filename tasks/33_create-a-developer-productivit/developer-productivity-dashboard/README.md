# Developer Productivity Dashboard

A modern web-based dashboard for analyzing Git repositories and visualizing developer productivity metrics. Built with Next.js, TypeScript, and Recharts.

## Features

### Core Metrics
- **Commit Frequency**: Track commits over time with interactive line charts
- **Language Distribution**: Visual breakdown of programming languages used
- **Hourly Activity**: Heatmap showing peak coding hours by day and time
- **Project Velocity**: Trends in commits and lines changed over time
- **Top Contributors**: Leaderboard of most active developers
- **Most Changed Files**: Identify files with highest modification frequency
- **Actionable Insights**: AI-generated recommendations based on patterns

### Technical Highlights
- 🚀 **Next.js 15** with App Router
- 🎨 **Tailwind CSS** for responsive styling
- 📊 **Recharts** for interactive visualizations
- 🔧 **TypeScript** for type safety
- 🎯 **Zustand** for lightweight state management
- 📦 **simple-git** for Git operations

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Git installed on your system
- A local Git repository to analyze

### Installation

1. Navigate to the project directory:
```bash
cd developer-productivity-dashboard
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

### Analyzing a Repository

1. Enter the full path to your Git repository
   - Linux/Mac: `/home/user/projects/my-app`
   - Windows: `C:\Users\user\projects\my-app`

2. Click "Analyze Repository"

3. View the interactive dashboard with:
   - Summary metrics cards
   - Commit frequency trends
   - Language distribution
   - Activity heatmap
   - Project velocity
   - Top contributors and files
   - Actionable insights

### Example Paths

```
/home/user/documents/github/project
~/projects/opensource/repo
C:\Projects\my-app
```

## Project Structure

```
developer-productivity-dashboard/
├── app/
│   ├── api/
│   │   ├── analyze/       # Repository analysis endpoint
│   │   └── validate/      # Repository validation endpoint
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Main dashboard page
├── components/
│   ├── ui/                # Reusable UI components
│   ├── charts/            # Chart components
│   ├── metrics/           # Metric display components
│   ├── RepositoryInput.tsx
│   └── InsightsPanel.tsx
├── lib/
│   ├── git/
│   │   ├── scanner.ts     # Git repository scanner
│   │   ├── parser.ts      # Git log parser
│   │   ├── metrics.ts     # Metrics calculator
│   │   └── types.ts       # Type definitions
│   ├── store.ts           # Zustand state management
│   └── utils.ts           # Utility functions
└── public/                # Static assets
```

## API Endpoints

### POST /api/analyze

Analyzes a Git repository and returns metrics.

**Request:**
```json
{
  "repoPath": "/path/to/repo",
  "options": {
    "since": "2024-01-01",
    "until": "2024-12-31",
    "author": "John Doe",
    "branch": "main"
  }
}
```

**Response:**
```json
{
  "repository": {
    "path": "/path/to/repo",
    "name": "my-repo",
    "branch": "main",
    "lastCommit": "abc123"
  },
  "metrics": {
    "totalCommits": 1234,
    "totalAuthors": 5,
    "commitFrequency": [...],
    "languageDistribution": [...],
    "hourlyActivity": [...],
    "velocity": [...],
    "topContributors": [...],
    "topFiles": [...]
  }
}
```

### POST /api/validate

Validates if a path is a valid Git repository.

**Request:**
```json
{
  "repoPath": "/path/to/repo"
}
```

**Response:**
```json
{
  "valid": true,
  "repository": {...},
  "branches": ["main", "develop"],
  "authors": ["John Doe", "Jane Smith"]
}
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | **Next.js 15** | Full-stack React framework with API routes |
| Language | **TypeScript** | Type-safe JavaScript |
| Styling | **Tailwind CSS** | Utility-first CSS framework |
| Charts | **Recharts** | Composable React charting library |
| Git | **simple-git** | Node.js wrapper for Git |
| State | **Zustand** | Lightweight state management |
| Icons | **Lucide React** | Beautiful icon library |

## Performance Considerations

- Large repositories may take longer to analyze
- Commits are limited to 10,000 for performance
- Charts automatically sample data for better rendering
- Consider filtering by date range for large repos

## Troubleshooting

### "Invalid Git repository" error
- Ensure the path points to a valid Git repository
- Check that the `.git` folder exists in the directory
- Verify you have read permissions for the repository

### Empty dashboard
- Check that the repository has commits
- Ensure the branch has commits
- Try analyzing the default branch (main/master)

### Performance issues
- Analyze smaller repositories first
- Use date range filtering
- Close other browser tabs

## Development

### Build for Production

```bash
npm run build
npm start
```

### Lint Code

```bash
npm run lint
```

## Future Enhancements

Potential features for future versions:

- [ ] Multi-repository comparison
- [ ] Historical snapshots and trends
- [ ] Goal tracking and streaks
- [ ] Export data as CSV/JSON
- [ ] Team collaboration features
- [ ] Custom date range filtering
- [ ] Dark mode support
- [ ] More advanced insights
- [ ] Integration with GitHub/GitLab APIs

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

Built with modern web technologies and open-source libraries:
- [Next.js](https://nextjs.org/)
- [Recharts](https://recharts.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [simple-git](https://github.com/steveukx/git-js)
