const PHOTOS = [
  "/images/atmosphere/d1.jpg",
  "/images/atmosphere/d2.jpg",
  "/images/atmosphere/d3.png",
  "/images/atmosphere/d4.png",
  "/images/atmosphere/d5.png",
  "/images/atmosphere/d6.jpg",
  "/images/atmosphere/d7.jpg",
];

export function AuthAtmosphere() {
  return (
    <div className="auth-mosaic" aria-hidden>
      {PHOTOS.map((src) => (
        <img key={src} src={src} alt="" />
      ))}
      <div className="auth-mosaic-dim" />
    </div>
  );
}
