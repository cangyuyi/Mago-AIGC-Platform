import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-[11px] text-sm font-medium transition-[background-color,color,box-shadow,transform] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#007aff]/30 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-45 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-[#007aff] text-white shadow-[0_2px_5px_rgba(0,122,255,0.2)] hover:bg-[#006de0]",
        primary: "bg-[#007aff] text-white shadow-[0_2px_5px_rgba(0,122,255,0.2)] hover:bg-[#006de0]",
        secondary: "bg-[#e9e9ed] text-[#1d1d1f] hover:bg-[#dedee3]",
        ghost: "text-[#6e6e73] hover:bg-black/[0.05] hover:text-[#1d1d1f]",
        danger: "bg-[#ff3b30] text-white hover:bg-[#e52f25]",
        outline: "border border-black/[0.1] bg-white text-[#1d1d1f] shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:bg-[#f7f7f8]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3 text-[13px]",
        lg: "h-11 px-6 text-[15px]",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => (
  <button className={buttonVariants({ variant, size, className })} ref={ref} {...props} />
));
Button.displayName = "Button";
export { Button, buttonVariants };
