%  Copyright (c) 2018 IRT-AESE.
%  All rights reserved.
%
%  Contributors:
%  - Nicolas Roussouly
%  - Antoine DECHAUME

function [x,y,z] = dummy_complex_fct(a,b,c,d,e,f)
%DUMMY_COMPLEX_FCT Summary of this function goes here
%   Detailed explanation goes here
% which(mfilename);
x = a+b;
try
    y=c*d;
catch
    y=c.*d;
end
try
    z = e/f;
catch
    z = e./f;
end

end
