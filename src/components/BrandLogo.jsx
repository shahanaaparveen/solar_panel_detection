import logoSvg from '../assets/company-logo.svg';

export default function BrandLogo({ compact = true, size = 1, style = {} }) {
  const width = compact ? 110 * size : 150 * size;

  return (
    <img
      src={logoSvg}
      alt="Sri Eshwar Drone Tech"
      style={{
        display: 'block',
        width: `${width}px`,
        maxHeight: '34px',
        height: 'auto',
        maxWidth: '100%',
        objectFit: 'contain',
        ...style,
      }}
    />
  );
}
