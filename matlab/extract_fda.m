function [image,code] = extract_fda(filepath)
%EXTRACT_OCT Extract fundus from topcon .fda file format. Mostly based on
%description of file format here: https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

fid = fopen(filepath);
code=1;
if fid == -1
    image = 0;
    code = -1;
    return
end


char(fread(fid,7));
fread(fid,1,'uint32');
fread(fid,1,'uint32');

eof = false;
while ~eof
    chunk_name_size = fread(fid,1);
    if chunk_name_size == 0
        eof = true;
    else
        chunk_name = char(fread(fid,chunk_name_size))';
        disp(chunk_name)
        chunk_size = fread(fid,1,'uint32');
        if strcmp(chunk_name, '@IMG_FUNDUS')
            %chunk_data = fread(fid,chunk_size);
            width = fread(fid,1,'uint32');
            height = fread(fid,1,'uint32');
            bits_per_pixel = fread(fid,1,'uint32');
            num_slices = fread(fid,1,'uint32');
            skip = fread(fid,1);
            size = fread(fid,1,'uint32');
            num_pixels = width*height*num_slices;
            raw_volume = fread(fid,size,'uint16');
            fundus2 = reshape(raw_volume,1,width,height);
            fundus2=permute(fundus2,[2,3,1]);
            fundus = fundus2;
            fundus(:,:,1) = fundus2(:,:,3);
            fundus(:,:,3) = fundus2(:,:,1);
%             bits_per_pixel = fread(fid,1,'uint32');
%             skip = fread(fid,1,'uint32');
%             num_pixels = width*height;
%             size = fread(fid,1,'uint32');
%             raw_volume = fread(fid,num_pixels,'uint16');
%             image = reshape(raw_volume,width,height);
        elseif strcmp(chunk_name, '@PARAM_SCAN_04')   
            fread(fid,6,'uint16');
            x_dim = fread(fid,1,'float64');
            y_dim = fread(fid,1,'float64');
            z_dim = fread(fid,1,'float64');
            fread(fid,2,'float64');
            fread(fid,9);
        else
            chunk_data = fread(fid,chunk_size);
        end
        
    end
end
