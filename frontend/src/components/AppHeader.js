import React from 'react';
import { Box, AppBar, Toolbar, Typography, IconButton } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { COMPANY_NAME, COMPANY_NAME_PREVIOUS } from '../constants';

/**
 * Shared app header: optional dark back arrow (far left), then logo + company name (gradient), then blue section.
 * rightContent: content for the blue section (e.g. title + buttons).
 * backTo: path to navigate when back is clicked; if not provided, no back button.
 */
const AppHeader = ({ backTo, rightContent }) => {
  const navigate = useNavigate();
  const showBack = backTo != null && backTo !== '';

  return (
    <Box sx={{ pt: 1.5, px: 1.5 }}>
      <AppBar
        position="static"
        sx={{
          backgroundColor: 'transparent',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          borderRadius: '16px',
          overflow: 'hidden',
        }}
      >
        <Toolbar sx={{ px: 0, minHeight: { xs: 64, sm: 72 }, width: '100%' }}>
          {showBack && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#fff',
                borderTopLeftRadius: 16,
                borderBottomLeftRadius: 16,
                width: 48,
                minWidth: 48,
                alignSelf: 'stretch',
              }}
            >
              <IconButton
                onClick={() => navigate(backTo)}
                sx={{ color: '#1a1a1a' }}
                aria-label="Back"
              >
                <ArrowBack />
              </IconButton>
            </Box>
          )}
          <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', width: '100%', minWidth: 0 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                background: 'linear-gradient(to right, #ffffff 0%, #e3f2fd 35%, #90caf9 70%, #1976d2 100%)',
                pr: 3,
                py: 0.5,
                pl: 2,
                borderTopLeftRadius: showBack ? 0 : 16,
                borderBottomLeftRadius: showBack ? 0 : 16,
              }}
            >
              <img
                src={process.env.PUBLIC_URL + '/logo.png'}
                alt=""
                style={{
                  height: 48,
                  width: 'auto',
                  maxWidth: 120,
                  objectFit: 'contain',
                  display: 'block',
                }}
                onError={(e) => {
                  const el = e.target;
                  if (!el.dataset.triedSvg) {
                    el.dataset.triedSvg = '1';
                    el.src = process.env.PUBLIC_URL + '/logo.svg';
                  }
                }}
              />
              <Box>
                <Typography variant="subtitle1" component="div" sx={{ fontWeight: 600, lineHeight: 1.2, color: '#1a1a1a' }}>
                  {COMPANY_NAME}
                </Typography>
                <Typography variant="subtitle1" component="div" sx={{ opacity: 0.9, color: '#1a1a1a' }}>
                  {COMPANY_NAME_PREVIOUS}
                </Typography>
              </Box>
            </Box>
            <Box
              sx={{
                flexGrow: 1,
                minWidth: 0,
                bgcolor: '#1976d2',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                px: 2,
                py: 0,
                alignSelf: 'stretch',
                borderTopRightRadius: 16,
                borderBottomRightRadius: 16,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', minWidth: 0 }}>
                {rightContent}
              </Box>
            </Box>
          </Box>
        </Toolbar>
      </AppBar>
    </Box>
  );
};

export default AppHeader;
