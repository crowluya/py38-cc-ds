# Technology Stack & Architecture

## Chosen Technology Stack

### Frontend Framework
**React 18 + Vite**
- **Why React?**
  - Component-based architecture perfect for modular UI
  - Large ecosystem and community support
  - Excellent state management with hooks
  - Easy to test and maintain

- **Why Vite?**
  - Lightning-fast development server
  - Optimized production builds
  - Native ES modules support
  - Better DX than Create React App

### State Management
**React Hooks + Context API**
- Local component state for UI interactions
- Context API for global state (settings, current session)
- No need for Redux (simple state requirements)

### Data Persistence
**IndexedDB (via Dexie.js)**
- **Why IndexedDB?**
  - Large storage capacity (hundreds of MB)
  - Asynchronous API for performance
  - Indexed queries for fast statistics
  - Works offline

- **Why Dexie.js?**
  - Simple, Promise-based API
  - Type-safe with TypeScript
  - Much easier than raw IndexedDB
  - Excellent documentation

**localStorage** for:
- User settings and preferences
- Theme selection
- Quick access data

### Styling
**Tailwind CSS**
- Utility-first CSS framework
- Rapid UI development
- Easy theming
- Small bundle size with tree-shaking
- Responsive design utilities

**Custom CSS** for:
- Special animations
- Complex components
- Print styles

### Data Visualization
**Chart.js (via react-chartjs-2)**
- Lightweight and flexible
- Beautiful default charts
- Responsive out of the box
- Easy to customize
- Good documentation

### Notifications & Audio
- **Web Notifications API** - Native browser notifications
- **Howler.js** - Audio management for alerts
- Browser native Audio API as fallback

### Build Tools & Development
- **TypeScript** - Type safety and better DX
- **ESLint** - Code quality
- **Prettier** - Code formatting
- **Vitest** - Unit testing
- **Playwright** - E2E testing

## Architecture Pattern

### Overall Architecture
**Single Page Application (SPA)**
- Client-side rendering
- Local-first data storage
- No backend dependency
- Progressive Web App (PWA) capabilities

### Project Structure
```
writing-timer/
├── public/
│   ├── favicon.ico
│   └── sounds/              # Audio files for notifications
├── src/
│   ├── components/
│   │   ├── timer/           # Timer-related components
│   │   ├── writing/         # Writing interface components
│   │   ├── statistics/      # Statistics dashboard
│   │   ├── settings/        # Settings panel
│   │   └── common/          # Shared components
│   ├── db/
│   │   ├── dexie.ts         # IndexedDB setup
│   │   └── migrations.ts    # Database migrations
│   ├── hooks/
│   │   ├── useTimer.ts      # Timer logic
│   │   ├── useStats.ts      # Statistics calculations
│   │   └── useNotification.ts # Notification management
│   ├── stores/
│   │   └── settingsStore.ts # Global settings state
│   ├── types/
│   │   └── index.ts         # TypeScript types
│   ├── utils/
│   │   ├── time.ts          # Time formatting utilities
│   │   ├── storage.ts       # Storage helpers
│   │   └── export.ts        # Data export/import
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### Component Architecture

**Smart Container Components**
- Manage state and business logic
- Connect to data layer
- Pass props to presentation components

**Presentational Components**
- Pure UI components
- Receive props, render UI
- No direct data access

Example:
- `<TimerContainer>` - Smart (manages timer state)
- `<TimerDisplay>` - Presentational (just shows time)

### Data Layer Architecture

**Repository Pattern**
```
Component → Hook → Repository → IndexedDB
```

- **Components** - UI layer
- **Custom Hooks** - Business logic layer
- **Repository** - Data access abstraction
- **IndexedDB** - Storage layer

### State Management Strategy

**Local State** (useState)
- Form inputs
- UI toggles (modals, panels)
- Temporary data

**Global State** (Context API)
- User settings
- Current active session
- Theme preference

**Server State** (IndexedDB via hooks)
- Session history
- Statistics data
- Cached calculations

## Design Patterns

### 1. Custom Hooks Pattern
Encapsulate reusable logic:
- `useTimer()` - Timer countdown and controls
- `useStats()` - Statistics aggregation
- `useNotification()` - Notification management
- `usePersistence()` - Auto-save logic

### 2. Provider Pattern
Wrap app with context providers:
```tsx
<SettingsProvider>
  <ThemeProvider>
    <NotificationProvider>
      <App />
    </NotificationProvider>
  </ThemeProvider>
</SettingsProvider>
```

### 3. Repository Pattern
Abstract data access:
```typescript
class SessionRepository {
  async save(session: Session) { }
  async getAll() { }
  async getStats() { }
}
```

### 4. Observer Pattern
Subscribe to timer changes:
```typescript
timer.on('tick', (timeLeft) => updateDisplay())
timer.on('complete', () => showNotification())
```

## Performance Considerations

### Optimization Strategies
1. **Code Splitting** - Lazy load routes/components
2. **Memoization** - React.memo for expensive components
3. **Debouncing** - Auto-save with 30s debounce
4. **Virtual Scrolling** - For long session lists
5. **IndexedDB Indexing** - Optimize query performance

### Bundle Size Targets
- Initial load: < 200KB gzipped
- Full app: < 500KB gzipped
- Lazy chunks: < 100KB each

## Security & Privacy

### Data Privacy
- All data stored locally
- No telemetry or analytics
- No external API calls
- User controls data export/deletion

### Best Practices
- Validate all user inputs
- Sanitize exported data
- Secure IndexedDB with basic checks
- No XSS vulnerabilities (React prevents by default)

## Accessibility

### WCAG 2.1 Compliance
- Keyboard navigation
- Screen reader support
- Focus indicators
- Color contrast ratios
- ARIA labels where needed

### Features
- Full keyboard control
- High contrast mode
- Text resizing support
- Focus management in modals

## Testing Strategy

### Unit Tests (Vitest)
- Custom hooks logic
- Utility functions
- Repository methods
- Statistics calculations

### Integration Tests
- Component interactions
- State management
- Data persistence

### E2E Tests (Playwright)
- Complete user flows
- Cross-browser testing
- Notification permissions
- Data export/import

## Deployment

### Build Process
1. Type checking
2. Linting
3. Unit tests
4. Build with Vite
5. Generate PWA assets

### Deployment Options
- **GitHub Pages** - Free static hosting
- **Netlify** - Drag-and-drop deployment
- **Vercel** - Automatic deployments
- **Local** - Can run entirely from file://

### PWA Capabilities
- Service worker for offline support
- App manifest for installability
- Responsive design for all devices
- Fast, reliable loading

## Development Workflow

### Git Workflow
```
main (production)
  └── develop (staging)
      └── feature/timer-component
      └── feature/statistics-dashboard
```

### Commit Convention
```
feat: add timer component
fix: correct notification timing
docs: update README
refactor: improve data layer
test: add statistics tests
```

## Maintenance & Scalability

### Future Considerations
- Modular architecture allows easy feature addition
- IndexedDB schema supports migrations
- Component structure supports theming
- Hooks pattern supports testing

### Extension Points
- Add new timer types (HIIT, custom intervals)
- Additional statistics visualizations
- Plugin system for custom behaviors
- Export to different formats (PDF, DOCX)

## Conclusion

This stack prioritizes:
1. **Developer Experience** - Fast iteration, good tooling
2. **User Experience** - Fast, responsive, offline-capable
3. **Maintainability** - Clean architecture, type safety
4. **Performance** - Small bundles, efficient rendering
5. **Privacy** - Local-first, no external dependencies
