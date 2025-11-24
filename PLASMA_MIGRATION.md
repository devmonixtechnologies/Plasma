# Plasma AI Migration Guide

This document outlines the migration from CAI (Cybersecurity AI) to Plasma AI branding.

## Brand Changes

### Project Identity
- **Old Name**: Cybersecurity AI (CAI)
- **New Name**: Plasma AI
- **Theme**: Modern indigo/violet gradient with plasma energy effects

### Visual Updates
- New logo with plasma energy core and shield design
- Updated color scheme: `#6366f1` → `#8b5cf6` gradients
- Advanced visual effects: glassmorphism, particle systems, shimmer animations
- Modern typography: Space Grotesk headings + Inter body text

### File Changes
- `README.md`: Updated project name, logo references, and branding
- `docs/stylesheets/extra.css`: Enhanced with advanced visual effects
- `media/plasma-logo-modern.svg`: New animated plasma logo
- `media/plasma-banner.svg`: New banner with plasma visualization
- `src/cai/cli.py`: Updated environment variable names (PLASMA_*)

## Environment Variables

### Updated Variable Names
```bash
# Old CAI variables
CAI_MODEL → PLASMA_MODEL
CAI_DEBUG → PLASMA_DEBUG
CAI_BRIEF → PLASMA_BRIEF
CAI_MAX_TURNS → PLASMA_MAX_TURNS
CAI_TRACING → PLASMA_TRACING
CAI_AGENT_TYPE → PLASMA_AGENT_TYPE
CAI_STATE → PLASMA_STATE
CAI_MEMORY → PLASMA_MEMORY
CAI_MEMORY_ONLINE → PLASMA_MEMORY_ONLINE
CAI_MEMORY_OFFLINE → PLASMA_MEMORY_OFFLINE
CAI_ENV_CONTEXT → PLASMA_ENV_CONTEXT
CAI_MEMORY_ONLINE_INTERVAL → PLASMA_MEMORY_ONLINE_INTERVAL
```

### Usage Examples
```bash
# Launch Plasma AI with a specific agent
PLASMA_AGENT_TYPE=redteam_agent plasma

# Launch with custom model
PLASMA_AGENT_TYPE=bug_bounter_agent PLASMA_MODEL=alias0 plasma

# Or switch agents during a session
Plasma>/agent redteam_agent

# List all available agents with descriptions
Plasma>/agent list
```

## New Features

### Advanced Visual Effects
- **Animated Background**: Subtle 15-second gradient shifting
- **Particle Systems**: Dynamic floating particles with plasma theme
- **Glassmorphism**: Modern frosted glass effects on components
- **Shimmer Effects**: Animated light sweeps on headers and CTAs
- **Neon Glow**: Pulsating text effects for futuristic feel
- **Advanced Hover**: Multi-layered hover with sweep animations

### Enhanced Components
- **Code Blocks**: Glassmorphism with animated borders
- **Tables**: Glowing borders with advanced hover scaling
- **Feature Cards**: Backdrop blur and micro-animations
- **CTA Boxes**: Shimmer effects and glassmorphism
- **Navigation**: Enhanced hover states and transitions

## Migration Checklist

- [ ] Update environment variables in scripts/config files
- [ ] Update documentation references
- [ ] Update CI/CD pipelines
- [ ] Test new visual effects in documentation
- [ ] Verify all branding is consistent

## Backward Compatibility

The project maintains backward compatibility with existing CAI functionality while introducing the new Plasma branding. All core features and agents remain unchanged.

## Support

For questions about the migration or Plasma AI features, please refer to the updated documentation or open an issue.
