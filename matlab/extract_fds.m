function [volume,fundus,code] = extract_fds(filepath)
%EXTRACT_OCT Extract OCT from topcon .fds file format. Mostly based on
%description of file format here: https://bitbucket.org/uocte/uocte/wiki/Topcon%20File%20Format

fid = fopen(filepath);
code=1;
if fid == -1
    volume = 0;
    code = -1;
    return
end
char(fread(fid,7))';
fread(fid,1,'uint32');
fread(fid,1,'uint32');

eof = false;
while ~eof
    chunk_name_size = fread(fid,1);
    if chunk_name_size == 0
        eof = true;
    else
        chunk_name = char(fread(fid,chunk_name_size))';
        chunk_size = fread(fid,1,'uint32');
        if strcmp(chunk_name,'@IMG_SCAN_03')
            %chunk_data = fread(fid,chunk_size);
            fread(fid,1);
            width = fread(fid,1,'uint32');
            height = fread(fid,1,'uint32');
            bits_per_pixel = fread(fid,1,'uint32');
            num_slices = fread(fid,1,'uint32');
            num_pixels = width*height*num_slices;
            skip = fread(fid,1);
            size = fread(fid,1,'uint32');
            raw_volume = fread(fid,num_pixels,'uint16');
            volume = reshape(raw_volume,width,height,num_slices);
            %         elseif strcmp(chunk_name,'@IMG_MOT_COMP_03')
            %             %chunk_data = fread(fid,chunk_size);
            %             fread(fid,1);
            %             width = fread(fid,1,'uint32')
            %             height = fread(fid,1,'uint32')
            %             bits_per_pixel = fread(fid,1,'uint32')
            %             num_slices = fread(fid,1,'uint32')
            %             fread(fid,17);
            %             size = fread(fid,1,'uint32')
            %             num_pixels = width*height*num_slices
            %             raw_volume = fread(fid,num_pixels,'uint16');
            %             volume = reshape(raw_volume,width,height,num_slices);
            %         elseif strcmp(chunk_name,'@IMG_TRC_02')
            %             width = fread(fid,1,'uint32');
            %             height = fread(fid,1,'uint32');
            %             bits_per_pixel = fread(fid,1,'uint32');
            %             num_slices = fread(fid,1,'uint32');
            %             a_thing = fread(fid,1);
            %             size = fread(fid,1,'uint32');
            %             num_pixels = width*height*num_slices;
            %             raw_volume = fread(fid,size);
            %             raw_volume2 = raw_volume(1:3:end);
            %             fundus = reshape(raw_volume2,width,height,num_slices);
        elseif strcmp(chunk_name,'@IMG_OBS')
            %chunk_data = fread(fid,chunk_size);
            width = fread(fid,1,'uint32');
            height = fread(fid,1,'uint32');
            bits_per_pixel = fread(fid,1,'uint32');
            num_slices = fread(fid,1,'uint32');
            a_thing = fread(fid,1);
            size = fread(fid,1,'uint32');
            num_pixels = width*height*num_slices;
            raw_volume = fread(fid,size);
            fundus2 = reshape(raw_volume,3,width,height);
            fundus2=permute(fundus2,[2,3,1]);
            fundus = fundus2;
            fundus(:,:,1) = fundus2(:,:,3);
            fundus(:,:,3) = fundus2(:,:,1);
        else
            chunk_data = fread(fid,chunk_size);
        end
        
    end
end
end

