import logoUrl from './tunibot-logo.png'

type BrandLogoProps = {
  className?: string
  imageClassName?: string
}

export default function BrandLogo({
  className = '',
  imageClassName = '',
}: BrandLogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`.trim()}>
      <img
        src={logoUrl}
        alt="Tunibot Automation"
        className={`shrink-0 ${imageClassName}`.trim()}
      />
    </div>
  )
}